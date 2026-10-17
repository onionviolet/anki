# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Local Mandarin TTS with optional MLX dependencies in a separate worker."""

from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path
from threading import Event

from anki.qwen_tts import SPEAKERS, QwenRuntime, QwenWorker, valid_audio
from anki.sound import AVTag, TTSTag
from aqt.sound import OnDoneCallback, Player
from aqt.taskman import TaskManager
from aqt.tts import TTSPlayer, TTSVoice, TTSVoiceMatch
from aqt.utils import tooltip, tr


class QwenTTSPlayer(Player, TTSPlayer):
    default_rank = 0

    def __init__(self, taskman: TaskManager) -> None:
        self._taskman = taskman
        self._cancelled: Event | None = None
        self._closed = False
        try:
            self._runtime = QwenRuntime.read()
        except (OSError, ValueError, KeyError, TypeError) as error:
            print(f"Optional Qwen runtime is unavailable: {error}")
            self._runtime = None
        self._worker = QwenWorker(self._runtime) if self._runtime else None

    def get_available_voices(self) -> list[TTSVoice]:
        if self._worker is None or self._closed:
            return []
        return [TTSVoice(f"Qwen3_{speaker}", "zh_CN") for speaker in SPEAKERS]

    def voice_for_tag(self, tag: TTSTag) -> TTSVoiceMatch | None:
        match = super().voice_for_tag(tag)
        if match and match.rank == -100:
            # Prefer Qwen for unqualified Mandarin, while explicit voice requests
            # still follow their template order across all TTS players.
            match.rank = -60
        return match

    def rank_for_tag(self, tag: AVTag) -> int | None:
        if self._closed or not isinstance(tag, TTSTag):
            return None
        match = self.voice_for_tag(tag)
        return match.rank if match else None

    def play(self, tag: AVTag, on_done: OnDoneCallback) -> None:
        assert isinstance(tag, TTSTag)
        assert self._worker is not None and self._runtime is not None
        match = self.voice_for_tag(tag)
        assert match is not None
        speaker = match.voice.name.removeprefix("Qwen3_")
        cancelled = self._cancelled = Event()
        try:
            path = self._runtime.audio_path(tag.field_text, speaker, tag.speed)
        except ValueError as error:
            tooltip(tr.weibao_qwen_error(error=str(error)))
            on_done()
            return
        if not valid_audio(path):
            tooltip(tr.weibao_qwen_generating())
        worker = self._worker
        self._taskman.run_in_background(
            lambda: worker.generate(tag.field_text, speaker, tag.speed, cancelled),
            lambda result: self._on_done(result, on_done, cancelled),
            uses_collection=False,
        )

    def _on_done(
        self, result: Future[Path], on_done: OnDoneCallback, cancelled: Event
    ) -> None:
        if self._closed or cancelled.is_set():
            return
        try:
            path = result.result()
            from aqt.sound import av_player

            av_player.insert_file(str(path))
        except Exception as error:
            tooltip(tr.weibao_qwen_error(error=str(error)))
        if self._cancelled is cancelled:
            self._cancelled = None
        on_done()

    def stop(self) -> None:
        if self._cancelled is not None:
            self._cancelled.set()
            if self._worker is not None:
                self._worker.abort()
            from aqt.sound import av_player

            if av_player.current_player is self:
                av_player.current_player = None

    def shutdown(self) -> None:
        self._closed = True
        self.stop()
        if self._worker is not None:
            self._worker.close()
        from aqt.sound import av_player

        if av_player.current_player is self:
            av_player.current_player = None
