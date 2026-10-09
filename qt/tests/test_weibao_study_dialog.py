# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

import pytest

from anki.collection import Collection
from anki.consts import CARD_TYPE_REV, QUEUE_TYPE_REV
from anki.lang import set_lang
from aqt.qt import QApplication, QWidget
from aqt.weibao.review_capture import marker_tag
from aqt.weibao.study_data import (
    NoteSnapshot,
    apply_repair,
    protected_fields,
    protection_tag,
)

if TYPE_CHECKING:
    from aqt.main import AnkiQt
    from aqt.weibao.study_dialog import StudyDialog


@pytest.fixture(scope="module")
def app() -> Iterator[QApplication]:
    old_platform = os.environ.get("QT_QPA_PLATFORM")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    application = QApplication.instance() or QApplication([])
    set_lang("en_US")
    yield cast(QApplication, application)
    if old_platform is None:
        os.environ.pop("QT_QPA_PLATFORM", None)
    else:
        os.environ["QT_QPA_PLATFORM"] = old_platform


@pytest.fixture
def dialog(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[StudyDialog]:
    from aqt.main import AnkiQt
    from aqt.weibao.study_dialog import StudyDialog

    col = Collection(str(tmp_path / "collection.anki2"))
    model = col.models.by_name("Basic")
    assert model
    note = col.new_note(model)
    note["Front"] = "合适"
    note["Back"] = "Suitable; appropriate."
    col.add_note(note, col.decks.get_current_id())
    card = note.cards()[0]
    card.type = CARD_TYPE_REV
    card.queue = QUEUE_TYPE_REV
    card.due = col.sched.today
    card.ivl = 10
    col.update_card(card)
    note.tags = [
        marker_tag("explanation", int(note.cards()[0].id)),
        protection_tag("Front"),
    ]
    col.update_note(note)
    main = QWidget()
    main.col = col  # type: ignore[attr-defined]
    main.pm = SimpleNamespace(profile={})  # type: ignore[attr-defined]

    def query(
        self: StudyDialog,
        op: Callable[[Collection], Any],
        success: Callable[[Any], None],
        _key: str,
    ) -> None:
        success(op(col))

    monkeypatch.setattr(StudyDialog, "_query", query)
    widget = StudyDialog(cast(AnkiQt, main))
    widget.show()
    app.processEvents()
    yield widget
    widget.close()
    app.processEvents()
    col.close()
    main.close()


def test_repair_preview_invalidates_acceptance_after_edit(dialog: StudyDialog) -> None:
    front, lock = dialog._repair_fields["Front"]
    assert front.isReadOnly()
    assert lock.isChecked()
    back, _ = dialog._repair_fields["Back"]
    back.selectAll()
    back.insertPlainText("Use 合适 for a suitable choice.")
    dialog._preview_repair()
    assert dialog.repair_accept.isEnabled()
    assert "Use 合适" in dialog.repair_preview.toPlainText()
    assert "Suitable; appropriate." in dialog.repair_preview.toPlainText()

    back.setPlainText("Another correction")
    assert not dialog.repair_accept.isEnabled()
    assert dialog._proposal is None
    assert (
        dialog.mw.col.get_note(dialog._snapshot.note_id)["Back"]
        == "Suitable; appropriate."
    )


def test_capture_preview_and_break_inputs_require_new_acceptance(
    dialog: StudyDialog,
) -> None:
    # Real widgets and a real isolated collection, with only the background queue
    # replaced at its boundary so this test is deterministic.
    before = dialog.mw.col.note_count()
    dialog._capture_fields["Front"].setPlainText("New term")
    dialog._capture_fields["Back"].setPlainText("Sentence context")
    dialog._preview_capture()
    assert dialog.capture_accept.isEnabled()
    assert "Sentence context" in dialog.capture_preview.toPlainText()
    assert dialog.mw.col.note_count() == before
    dialog.source_title.setText("Changed source")
    assert not dialog.capture_accept.isEnabled()
    assert dialog._draft is None

    dialog._preview_break()
    assert dialog.break_accept.isEnabled()
    dialog.break_days.setValue(4)
    assert not dialog.break_accept.isEnabled()
    assert dialog._plan is None


def test_native_tabs_render_and_protection_is_visible(
    dialog: StudyDialog, app: QApplication
) -> None:
    note = dialog.mw.col.get_note(dialog._snapshot.note_id)
    assert protected_fields(note) == {"Front"}
    assert NoteSnapshot.read(note) == dialog._snapshot
    assert dialog.tabs.count() == 5
    # Optional synthetic screenshots for visual review; never use a real profile.
    if directory := os.environ.get("ANKI_STUDY_SCREENSHOTS"):
        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        dialog._repair_fields["Back"][0].setPlainText(
            "合适 describes a suitable choice or fit."
        )
        dialog._preview_repair()
        dialog._capture_fields["Front"].setPlainText("学习")
        dialog._capture_fields["Back"].setPlainText("Study; learn.\n我喜欢学习中文。")
        dialog.source_title.setText("Synthetic example")
        dialog.source_url.setText("https://example.org/lesson")
        dialog.source_field.setCurrentIndex(dialog.source_field.findData("Back"))
        dialog._preview_capture()
        dialog._preview_break()
        dialog.mw.col.set_config("fsrs", True)
        dialog._compare_retention()
        for index, name in enumerate(
            ("overview", "repairs", "capture", "break", "retention")
        ):
            dialog.tabs.setCurrentIndex(index)
            app.processEvents()
            assert dialog.grab().save(str(destination / f"{name}.png"))


@pytest.mark.parametrize("edit_other_field", [False, True])
def test_repair_preserves_untouched_unicode_and_line_endings(
    dialog: StudyDialog, edit_other_field: bool
) -> None:
    note = dialog.mw.col.get_note(dialog._snapshot.note_id)
    original = "NBSP: a\u00a0b\nline\u2028end"
    note["Front"] = original
    note["Back"] = original
    dialog.mw.col.update_note(note)
    note = dialog.mw.col.get_note(note.id)
    dialog._show_repair((NoteSnapshot.read(note), frozenset({"Front"})))
    if edit_other_field:
        editor = dialog._repair_fields["Back"][0]
        editor.selectAll()
        editor.insertPlainText("Deliberate correction")
    dialog._preview_repair()
    assert dialog._proposal is not None
    apply_repair(dialog.mw.col, dialog._proposal)
    saved = dialog.mw.col.get_note(note.id)
    assert saved["Front"] == original
    assert saved["Back"] == ("Deliberate correction" if edit_other_field else original)


def test_capture_operation_preserves_pending_repair_and_uses_main_progress_parent(
    dialog: StudyDialog, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import MagicMock

    dialog._repair_fields["Back"][0].insertPlainText("pending repair")
    dialog._preview_repair()
    proposal = dialog._proposal
    editor = dialog._repair_fields["Back"][0]
    operation = MagicMock()
    operation.success.return_value = operation
    operation.failure.return_value = operation
    constructor = MagicMock(return_value=operation)
    monkeypatch.setattr("aqt.weibao.study_dialog.CollectionOp", constructor)
    overview = MagicMock()
    monkeypatch.setattr(dialog, "refresh_overview", overview)
    dialog._mutate(lambda col: None, "capture")
    assert constructor.call_args.args[0] is dialog.mw
    operation.success.call_args.args[0](None)
    assert dialog._proposal is proposal
    assert dialog._repair_fields["Back"][0] is editor
    overview.assert_called_once()


def test_overview_refreshes_after_external_operation(
    dialog: StudyDialog, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import MagicMock

    from anki.collection import OpChanges
    from aqt import gui_hooks

    overview = MagicMock()
    repairs = MagicMock()
    monkeypatch.setattr(dialog, "refresh_overview", overview)
    monkeypatch.setattr(dialog, "refresh_repairs", repairs)
    gui_hooks.operation_did_execute(OpChanges(card=True), None)
    overview.assert_called_once()
    repairs.assert_not_called()


def test_repair_preview_preserves_crlf_original(dialog: StudyDialog) -> None:
    from dataclasses import replace

    original = "a\u00a0b\r\nline\u2028end"
    snapshot = replace(
        dialog._snapshot, fields=(("Front", original), ("Back", original))
    )
    dialog._show_repair((snapshot, frozenset({"Front"})))
    dialog._repair_fields["Back"][0].selectAll()
    dialog._repair_fields["Back"][0].insertPlainText("edited")
    dialog._preview_repair()
    assert dialog._proposal is not None
    assert dialog._proposal.fields == (("Front", original), ("Back", "edited"))
