# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Synthetic runtime add-on: real card rendering, generation and MPV playback."""

import os
import time
import traceback
from pathlib import Path

import aqt
from anki.decks import DeckId
from anki.sound import TTSTag
from aqt import gui_hooks, sound
from aqt.qt import QTimer
from aqt.weibao.qwen_tts import QwenTTSPlayer

base = Path(os.environ["QWEN_RUNTIME_BASE"])
played = []
beats = 0


def record(text):
    with (base / "report.txt").open("a") as file:
        file.write(text + "\n")


def heartbeat():
    global beats
    beats += 1
    QTimer.singleShot(25, heartbeat)


gui_hooks.av_player_did_begin_playing.append(
    lambda player, tag: played.append(type(player).__name__)
)


def scenarios():
    mw = aqt.mw
    player = next(p for p in sound.av_player.players if isinstance(p, QwenTTSPlayer))
    assert player._worker is not None and player._runtime is not None
    sound.mpvManager.command("set", "ao", "null")
    model = mw.col.models.by_name("Basic")
    model["tmpls"][0]["qfmt"] = (
        "<div>{{Front}}</div>{{tts zh_CN voices=Qwen3_Vivian:Front}}"
    )
    mw.col.models.update_dict(model)
    note = mw.col.new_note(model)
    text = "我们来学习银行和行业的读音。"
    note["Front"], note["Back"] = text, "Synthetic speech probe"
    mw.col.add_note(note, DeckId(1))
    card = note.cards()[0]
    tags = card.question_av_tags()
    assert len(tags) == 1 and isinstance(tags[0], TTSTag)
    assert tags[0].voices == ["Qwen3_Vivian"]
    conf = mw.col.decks.get_config(1)
    conf["autoplay"] = False
    mw.col.decks.update_config(conf)
    mw.moveToState("review")
    yield lambda: mw.reviewer.card is not None and mw.reviewer.state == "question"
    start = time.monotonic()
    before = beats
    mw.reviewer.replayAudio()
    yield (
        lambda: (
            bool(played)
            and sound.av_player.current_player is None
            and sound.av_player.queue_is_empty()
        )
    )
    first_time = time.monotonic() - start
    assert "MpvManager" in played
    assert beats > before + 10
    path = player._runtime.audio_path(text, "Vivian", 1.0)
    assert path.is_file()
    original = path.read_bytes()
    process = player._worker._process
    assert process is not None and process.poll() is None
    record(
        f"PASS reviewer generation and MPV completion; UI heartbeat active; first generation/playback {first_time:.2f}s"
    )
    played.clear()
    start = time.monotonic()
    mw.reviewer.replayAudio()
    yield lambda: bool(played) and sound.av_player.current_player is None
    assert player._worker._process is process and path.read_bytes() == original
    record(
        f"PASS cached replay reuses exact WAV and warm worker; playback {time.monotonic() - start:.2f}s"
    )
    played.clear()
    sound.av_player.play_tags(
        [
            TTSTag(
                "这段语音用于检查取消播放和切换用户。",
                "zh_CN",
                ["Qwen3_Serena"],
                1.0,
                [],
            )
        ]
    )
    yield lambda: player._cancelled is not None
    mw.unloadProfile(lambda: (mw.pm.load("QwenSecond"), mw.loadProfile()))
    yield (
        lambda: (
            mw.pm.name == "QwenSecond"
            and mw.col is not None
            and process.poll() is not None
        )
    )
    assert player._closed and player._worker._process is None
    assert mw.col.note_count() == 0
    yield lambda: mw.taskman._no_collection_executor._work_queue.empty()
    assert sound.av_player.current_player is None and sound.av_player.queue_is_empty()
    assert not played
    record(
        "PASS cancellation and profile switch release model process and discard late audio"
    )
    record("PASS all")
    mw.unloadProfileAndExit()


iterator = None
pending = None
deadline = 0


def tick():
    global pending, deadline
    try:
        if pending is not None and not pending():
            assert time.monotonic() < deadline, "Qwen runtime condition timed out"
            QTimer.singleShot(25, tick)
            return
        pending = next(iterator)
        deadline = time.monotonic() + 180
        QTimer.singleShot(25, tick)
    except StopIteration:
        return
    except Exception:
        record(traceback.format_exc())
        aqt.mw.unloadProfileAndExit()


def start():
    global iterator
    if iterator is None:
        iterator = scenarios()
        heartbeat()
        QTimer.singleShot(500, tick)


gui_hooks.profile_did_open.append(start)
