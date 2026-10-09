# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Temporary add-on driving real Qt operations, with native file dialogs replaced."""

import importlib.util
import json
import math
import os
import struct
import time
import traceback
import urllib.request
import wave
from pathlib import Path

import aqt
from aqt import gui_hooks
from aqt.operations import QueryOp
from aqt.operations.collection import undo
from aqt.qt import QPushButton, QTimer
from aqt.utils import tr
from aqt.weibao import study_dialog as sd
from aqt.weibao.review_capture import marker_tag
from aqt.weibao.study_data import protection_tag

base = Path(os.environ["STUDY_RUNTIME_BASE"])
report = base / "report.txt"
errors = []
playback = []
sd.showWarning = lambda text, **kwargs: errors.append(text)
gui_hooks.av_player_did_begin_playing.append(
    lambda player, tag: playback.append("begin")
)
gui_hooks.av_player_did_end_playing.append(lambda player: playback.append("end"))


def record(text):
    with report.open("a") as file:
        file.write(text + "\n")
    print(text, flush=True)


def click(dialog, text):
    buttons = [b for b in dialog.findChildren(QPushButton) if b.text() == text]
    assert len(buttons) == 1, text
    buttons[0].click()


def idle():
    return aqt.mw._background_op_count == 0


def scenarios():
    mw = aqt.mw
    record(
        "INFO optional provider dependencies: "
        + ", ".join(
            f"{name}={'available' if importlib.util.find_spec(name) else 'absent'}"
            for name in ("databind", "pydub")
        )
    )
    col = mw.col
    if os.environ.get("STUDY_RUNTIME_HELPER_SOURCE"):
        assert any(a.text() == "FSRS Helper" for a in mw.form.menuTools.actions())
        config = json.loads((base / "addons21/759844606/config.json").read_text())
        assert not any(
            config[key]
            for key in (
                "auto_reschedule_after_sync",
                "auto_disperse_after_sync",
                "auto_disperse_when_review",
                "auto_disperse_after_reschedule",
            )
        )
        record(
            "PASS optional FSRS Helper loads alongside Study tools with automatic scheduling disabled"
        )
    model = col.models.by_name("Basic")
    note = col.new_note(model)
    note["Front"], note["Back"] = "Synthetic term", "Original explanation"
    col.add_note(note, col.decks.get_current_id())
    card = note.cards()[0]
    card.type = card.queue = 2
    card.ivl, card.due = 10, col.sched.today
    col.update_card(card)
    note.tags = [marker_tag("explanation", int(card.id)), protection_tag("Front")]
    col.update_note(note)
    col.set_config("fsrs", True)
    mw.reset()
    actions = [
        a for a in mw.form.menuTools.actions() if a.text() == tr.weibao_study_tools()
    ]
    assert len(actions) == 1
    actions[0].trigger()
    yield idle
    d = next(w for w in mw.app.topLevelWidgets() if isinstance(w, sd.StudyDialog))
    assert d.overview.rowCount() == 1 and d._snapshot.note_id == note.id
    assert d._repair_fields["Front"][0].isReadOnly()
    record("PASS Tools entry and real asynchronous overview/repair/setup")
    proposal = base / "proposal.json"
    sd.QFileDialog.getSaveFileName = lambda *args: (str(proposal), "JSON")
    sd.QFileDialog.getOpenFileName = lambda *args: (str(proposal), "JSON")
    click(d, tr.weibao_export_snapshot())
    data = json.loads(proposal.read_text())
    data["changes"] = {"Back": "Accepted correction"}
    proposal.write_text(json.dumps(data))
    click(d, tr.weibao_import_proposal())
    assert (
        d.repair_accept.isEnabled()
        and col.get_note(note.id)["Back"] == "Original explanation"
    )
    d.repair_accept.click()
    yield idle
    assert col.get_note(note.id)["Back"] == "Accepted correction"
    undo(parent=mw)
    yield idle
    assert col.get_note(note.id)["Back"] == "Original explanation"
    d.refresh_repairs()
    yield idle
    data["changes"] = {"Front": "Forbidden"}
    proposal.write_text(json.dumps(data))
    click(d, tr.weibao_import_proposal())
    assert errors and "unlock" in errors.pop().lower()
    d._repair_fields["Back"][0].setPlainText("Stale correction")
    d._preview_repair()
    changed = col.get_note(note.id)
    changed["Back"] = "External edit"
    col.update_note(changed)
    d.repair_accept.click()
    yield idle
    assert errors and "changed" in errors.pop().lower()
    assert col.get_note(note.id)["Back"] == "External edit"
    record(
        "PASS proposal export/import/accept/undo, protected import and stale write rejection"
    )
    api_results = []

    def api_checks(_col):
        replies = []
        for action, params in (
            ("version", {}),
            ("modelFieldNames", {"modelName": "Basic"}),
            (
                "canAddNotes",
                {
                    "notes": [
                        {
                            "deckName": "Default",
                            "modelName": "Basic",
                            "fields": {"Front": "Browser preview", "Back": "Context"},
                            "tags": [],
                        }
                    ]
                },
            ),
            (
                "guiAddCards",
                {
                    "note": {
                        "deckName": "Default",
                        "modelName": "Basic",
                        "fields": {
                            "Front": "Browser preview",
                            "Back": "Context https://example.org",
                        },
                        "tags": ["synthetic"],
                    }
                },
            ),
        ):
            request = urllib.request.Request(
                "http://127.0.0.1:8779",
                data=json.dumps(
                    {"action": action, "version": 6, "params": params}
                ).encode(),
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                reply = json.load(response)
            assert reply["error"] is None, reply
            replies.append(reply["result"])
        return replies

    QueryOp(
        parent=mw, op=api_checks, success=api_results.append
    ).without_collection().run_in_background()
    yield lambda: bool(api_results) and idle()
    assert api_results[0][:3] == [6, ["Front", "Back"], [True]], api_results
    add = aqt.dialogs._dialogs["AddCards"][1]
    assert add.editor.note["Front"] == "Browser preview" and col.note_count() == 1
    add.grab().save(str(base / "browser-preview.png"))
    add.editor.set_note(col.new_note(model))
    add.close()
    yield idle
    record(
        "PASS AnkiConnect v6 fields/duplicates/guiAddCards: browser draft opens without adding a note"
    )
    d.tabs.setCurrentIndex(2)
    d.capture_model.setCurrentIndex(d.capture_model.findText("Basic"))
    d._capture_fields["Front"].setPlainText("Captured term")
    d._capture_fields["Back"].setPlainText("Context sentence")
    d.source_title.setText("Synthetic source")
    d.source_url.setText("https://example.org/study")
    d.source_field.setCurrentIndex(d.source_field.findData("Back"))
    d.audio_field.setCurrentIndex(d.audio_field.findData("Back"))
    audio = base / "tone.wav"
    with wave.open(str(audio), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(22050)
        wav.writeframes(
            b"".join(
                struct.pack("<h", int(2000 * math.sin(i * 2 * math.pi * 440 / 22050)))
                for i in range(11025)
            )
        )
    sd.QFileDialog.getOpenFileName = lambda *args: (str(audio), "WAV")
    # Exercise the optional no-provider-cost system voice route when requested.
    if system_audio := os.environ.get("STUDY_RUNTIME_AUDIO"):
        audio = Path(system_audio)
        sd.QFileDialog.getOpenFileName = lambda *args: (str(audio), "WAV")
    click(d, tr.weibao_audio_file())
    click(d, tr.weibao_play_audio())
    yield lambda: "end" in playback
    assert playback == ["begin", "end"], playback
    d._preview_capture()
    yield idle
    assert d.capture_accept.isEnabled()
    # A competing write after preview must be rejected again at acceptance.
    competing = col.new_note(model)
    competing["Front"] = "Captured term"
    col.add_note(competing, col.decks.get_current_id())
    d.capture_accept.click()
    yield idle
    assert errors and "duplicate" in errors.pop().lower()
    assert col.note_count() == 2
    undo(parent=mw)
    yield idle
    d._preview_capture()
    yield idle
    d.capture_accept.click()
    yield idle
    captured = col.find_notes('"Captured term"')
    assert len(captured) == 1
    saved = col.get_note(captured[0])["Back"]
    assert "https://example.org/study" in saved and f"[sound:{audio.name}]" in saved
    d._preview_capture()
    yield idle
    assert errors and "duplicate" in errors.pop().lower()
    undo(parent=mw)
    yield idle
    assert col.note_count() == 1
    record(
        "PASS capture preview/add/duplicate rejection/undo, source metadata and real MPV playback completion"
    )
    d.tabs.setCurrentIndex(3)
    d._preview_break()
    yield idle
    original = col.get_card(card.id)._to_backend_card().SerializeToString()
    assert len(d._plan.moves) == 1
    d.break_accept.click()
    yield idle
    assert col.get_card(card.id).due == col.sched.today + 3
    undo(parent=mw)
    yield idle
    assert col.get_card(card.id)._to_backend_card().SerializeToString() == original
    d._preview_break()
    yield idle
    changed = col.get_card(card.id)
    changed.due += 1
    col.update_card(changed)
    d.break_accept.click()
    yield idle
    assert errors and "schedule changed" in errors.pop().lower()
    record("PASS planned break preview/apply/undo and stale schedule rejection")

    def collection_state():
        tables = col.db.list(
            "select name from sqlite_master where type='table' order by name"
        )
        return [
            (name, col.db.all('select * from "' + name.replace('"', '""') + '"'))
            for name in tables
        ], col.undo_status()

    before = collection_state()
    d.tabs.setCurrentIndex(4)
    d._compare_retention()
    yield idle
    assert d.retention_table.rowCount() == 3
    assert before == collection_state()
    d.refresh_repairs()
    yield idle
    d._repair_fields["Back"][0].setPlainText("Preview-only correction")
    d._preview_repair()
    d._preview_capture()
    d._preview_break()
    yield idle
    for index, name in enumerate(
        ("overview", "repairs", "capture", "break", "retention")
    ):
        d.tabs.setCurrentIndex(index)
        yield lambda: True
        d.grab().save(str(base / f"{name}.png"))
    d.tabs.setCurrentIndex(2)
    area = d.tabs.widget(2)
    area.verticalScrollBar().setValue(area.verticalScrollBar().maximum())
    yield lambda: True
    d.grab().save(str(base / "capture-accept.png"))
    record("PASS retention comparison leaves every collection table and undo unchanged")
    d.close()
    mw.deckBrowser.show()
    yield idle
    # Execute the same JS used by the rendered home button in the actual webview.
    mw.web.eval("pycmd('weibao:study-tools')")
    yield lambda: any(
        isinstance(w, sd.StudyDialog) and w.isVisible()
        for w in mw.app.topLevelWidgets()
    )
    d = next(
        w
        for w in mw.app.topLevelWidgets()
        if isinstance(w, sd.StudyDialog) and w.isVisible()
    )
    yield idle
    record("PASS deck-home JS entry")
    late = []
    d._query(lambda col: col.note_count(), late.append, "close-probe")
    mw.unloadProfile(lambda: (mw.pm.load("SecondRuntime"), mw.loadProfile()))
    yield lambda: mw.pm.name == "SecondRuntime" and mw.col is not None and idle()
    assert d._closed and not late
    assert not any(
        isinstance(w, sd.StudyDialog) and w.isVisible()
        for w in mw.app.topLevelWidgets()
    )
    assert mw.col.note_count() == 0
    actions[0].trigger()
    yield idle
    d2 = next(
        w
        for w in mw.app.topLevelWidgets()
        if isinstance(w, sd.StudyDialog) and w.isVisible()
    )
    assert d2.repair_notes.count() == 0
    d2.close()
    record(
        "PASS profile switch drops late query callback and closes dashboard; fresh profile has no old data"
    )
    assert not errors, errors
    record("PASS all")
    mw.unloadProfileAndExit()


iterator = None
pending = None
deadline = 0


def tick():
    global pending, deadline
    try:
        if pending is not None and not pending():
            assert time.monotonic() < deadline, "Runtime condition timed out"
            QTimer.singleShot(25, tick)
            return
        pending = next(iterator)
        deadline = time.monotonic() + 25
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
        QTimer.singleShot(500, tick)


gui_hooks.profile_did_open.append(start)
