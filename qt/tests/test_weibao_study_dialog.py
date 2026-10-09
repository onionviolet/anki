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
from aqt.weibao.study_data import NoteSnapshot, protected_fields, protection_tag

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
    back.setPlainText("Use 合适 for a suitable choice.")
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
