# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from concurrent.futures import Future
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import aqt
from anki.qwen_tts import QwenRuntime
from anki.sound import TTSTag
from aqt.sound import AVPlayer
from aqt.tts import MacTTSPlayer, MacVoice
from aqt.weibao.qwen_tts import QwenTTSPlayer


@pytest.fixture
def player(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> QwenTTSPlayer:
    runtime = QwenRuntime(
        tmp_path / "python", tmp_path / "model", "test", tmp_path / "audio"
    )
    monkeypatch.setattr(QwenRuntime, "read", lambda *args: runtime)
    monkeypatch.setattr("aqt.weibao.qwen_tts.tooltip", MagicMock())
    monkeypatch.setattr("aqt.weibao.qwen_tts.tr", MagicMock())
    return QwenTTSPlayer(MagicMock())


@pytest.mark.parametrize(
    "requested,expected",
    [
        ([], QwenTTSPlayer),
        (["Qwen3_Serena"], QwenTTSPlayer),
        (["Apple_Tingting"], MacTTSPlayer),
        (["Apple_Tingting", "Qwen3_Vivian"], MacTTSPlayer),
        (["Qwen3_Vivian", "Apple_Tingting"], QwenTTSPlayer),
    ],
)
def test_qwen_voice_selection_respects_explicit_template_order(
    player: QwenTTSPlayer, requested: list[str], expected: type
) -> None:
    apple = MacTTSPlayer(MagicMock())
    apple._available_voices = [MacVoice("Apple_Tingting", "zh_CN", "Tingting")]
    queue = AVPlayer()
    queue.players = [apple, player]

    chosen = queue._best_player_for_tag(TTSTag("你好", "zh_CN", requested, 1, []))

    assert isinstance(chosen, expected)


def test_qwen_is_unavailable_without_setup_and_for_other_languages(
    monkeypatch: pytest.MonkeyPatch, player: QwenTTSPlayer
) -> None:
    assert player.rank_for_tag(TTSTag("你好", "zh_TW", [], 1, [])) is None
    assert player.rank_for_tag(TTSTag("Hello", "en_US", [], 1, [])) is None
    monkeypatch.setattr(QwenRuntime, "read", lambda *args: None)
    assert (
        QwenTTSPlayer(MagicMock()).rank_for_tag(TTSTag("你好", "zh_CN", [], 1, []))
        is None
    )


def test_qwen_stop_drops_late_audio_and_completion_callback(
    player: QwenTTSPlayer, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    queue = AVPlayer()
    queue.players = [player]
    monkeypatch.setattr(aqt.sound, "av_player", queue)
    player._worker = MagicMock()
    done = MagicMock()
    queue.current_player = player
    player.play(TTSTag("你好", "zh_CN", [], 1, []), done)
    pending = player._taskman.run_in_background.call_args.args[1]
    result: Future[Path] = Future()
    result.set_result(tmp_path / "old-card.wav")

    player.stop()
    pending(result)

    assert queue.current_player is None
    assert queue.queue_is_empty()
    done.assert_not_called()
    player._worker.abort.assert_called_once()


def test_qwen_close_drops_late_failure_and_releases_worker(
    player: QwenTTSPlayer, monkeypatch: pytest.MonkeyPatch
) -> None:
    queue = AVPlayer()
    queue.players = [player]
    monkeypatch.setattr(aqt.sound, "av_player", queue)
    player._worker = MagicMock()
    done = MagicMock()
    player.play(TTSTag("你好", "zh_CN", [], 1, []), done)
    pending = player._taskman.run_in_background.call_args.args[1]
    result: Future[Path] = Future()
    result.set_exception(RuntimeError("Worker stopped"))

    player.shutdown()
    pending(result)

    done.assert_not_called()
    player._worker.close.assert_called_once()
    assert player.rank_for_tag(TTSTag("你好", "zh_CN", [], 1, [])) is None


def test_qwen_failure_finishes_queue_instead_of_stalling(
    player: QwenTTSPlayer, monkeypatch: pytest.MonkeyPatch
) -> None:
    queue = AVPlayer()
    queue.players = [player]
    monkeypatch.setattr(aqt.sound, "av_player", queue)
    done = MagicMock()
    player.play(TTSTag("你好", "zh_CN", [], 1, []), done)
    pending = player._taskman.run_in_background.call_args.args[1]
    result: Future[Path] = Future()
    result.set_exception(RuntimeError("Generation failed"))

    pending(result)

    done.assert_called_once()
