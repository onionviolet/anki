# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from anki.collection import Collection
from anki.consts import CARD_TYPE_REV, QUEUE_TYPE_REV, QUEUE_TYPE_SUSPENDED
from anki.decks import DeckId
from anki.lang import set_lang
from anki.notes import Note
from aqt.weibao.review_capture import marker_tag
from aqt.weibao.study_data import (
    CaptureDraft,
    NoteSnapshot,
    RepairProposal,
    add_capture,
    apply_break,
    apply_repair,
    capture_note,
    compare_retention,
    deck_summaries,
    field_diff,
    import_repair_file,
    plan_break,
    protected_fields,
    protection_tag,
    repair_file,
)


@pytest.fixture
def col(tmp_path: Path) -> Iterator[Collection]:
    set_lang("en_US")
    collection = Collection(str(tmp_path / "collection.anki2"))
    yield collection
    collection.close()


def add_note(col: Collection, text: str = "sample") -> Note:
    model = col.models.by_name("Basic")
    assert model
    note = col.new_note(model)
    note["Front"] = text
    note["Back"] = "original explanation"
    col.add_note(note, DeckId(1))
    return note


def review_note(col: Collection, text: str, due: int) -> Note:
    note = add_note(col, text)
    card = note.cards()[0]
    card.type = CARD_TYPE_REV
    card.queue = QUEUE_TYPE_REV
    card.due = col.sched.today + due
    card.ivl = 10
    col.update_card(card)
    return note


def test_repair_preserves_review_state_resolves_marker_and_undoes(
    col: Collection,
) -> None:
    note = review_note(col, "repair", 5)
    card = note.cards()[0]
    note.tags = ["keep", marker_tag("explanation", int(card.id))]
    col.update_note(note)
    before = NoteSnapshot.read(note)
    schedule = card._to_backend_card().SerializeToString()
    proposal = RepairProposal(
        before,
        (("Front", "repair"), ("Back", "corrected")),
        frozenset({"Back"}),
        frozenset({note.tags[1]}),
    )

    apply_repair(col, proposal)

    saved = col.get_note(note.id)
    assert saved["Back"] == "corrected"
    assert set(saved.tags) == {"keep", protection_tag("Back")}
    assert protected_fields(saved) == {"Back"}
    assert col.get_card(card.id)._to_backend_card().SerializeToString() == schedule
    col.undo()
    assert NoteSnapshot.read(col.get_note(note.id)) == before


def test_repair_rejects_stale_snapshot_without_overwriting(col: Collection) -> None:
    note = add_note(col)
    proposal = RepairProposal(
        NoteSnapshot.read(note),
        (("Front", "sample"), ("Back", "proposal")),
        frozenset(),
        frozenset(),
    )
    note["Back"] = "edited elsewhere"
    col.update_note(note)

    with pytest.raises(ValueError, match="changed after preview"):
        apply_repair(col, proposal)
    assert col.get_note(note.id)["Back"] == "edited elsewhere"


def test_protected_field_requires_separate_unlock(col: Collection) -> None:
    note = add_note(col)
    note.tags = [protection_tag("Back")]
    col.update_note(note)
    before = NoteSnapshot.read(note)
    proposal = RepairProposal(
        before, (("Front", "sample"), ("Back", "replacement")), frozenset(), frozenset()
    )
    with pytest.raises(ValueError, match="Unlock Back"):
        apply_repair(col, proposal)
    assert NoteSnapshot.read(col.get_note(note.id)) == before

    apply_repair(col, replace(proposal, fields=before.fields))
    unlocked = NoteSnapshot.read(col.get_note(note.id))
    apply_repair(col, replace(proposal, before=unlocked))
    assert col.get_note(note.id)["Back"] == "replacement"


def test_repair_cannot_remove_unrelated_tags_or_omit_fields(col: Collection) -> None:
    note = add_note(col)
    note.tags = ["personal"]
    col.update_note(note)
    before = NoteSnapshot.read(note)
    proposal = RepairProposal(
        before, before.fields, frozenset(), frozenset({"personal"})
    )
    with pytest.raises(ValueError, match="Only existing repair markers"):
        apply_repair(col, proposal)
    with pytest.raises(ValueError, match="each current field"):
        apply_repair(col, replace(proposal, fields=(("Front", "changed"),)))
    assert NoteSnapshot.read(col.get_note(note.id)) == before


def test_diff_displays_html_as_text() -> None:
    result = field_diff(
        (("<field>", "old"),), (("<field>", '<script>alert("x")</script>'),)
    )
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
    assert "&lt;field&gt;" in result


def test_imported_proposal_requires_matching_snapshot_and_respects_protection() -> None:
    snapshot = NoteSnapshot(
        123,
        456,
        (("Front", "question"), ("Back", "old explanation")),
        (protection_tag("Front"),),
    )
    data = json.loads(repair_file(snapshot))
    data["changes"] = {"Back": "proposed correction"}
    assert import_repair_file(json.dumps(data), snapshot) == (
        ("Front", "question"),
        ("Back", "proposed correction"),
    )
    assert dict(snapshot.fields)["Back"] == "old explanation"
    data["changes"] = {"Front": "replace protected question"}
    with pytest.raises(ValueError, match="Unlock Front"):
        import_repair_file(json.dumps(data), snapshot)
    data["changes"] = {"Missing": "invalid field"}
    with pytest.raises(ValueError, match="existing field names"):
        import_repair_file(json.dumps(data), snapshot)
    data["changes"] = {}
    data["expected_fields"]["Back"] = "stale"
    with pytest.raises(ValueError, match="does not match"):
        import_repair_file(json.dumps(data), snapshot)


def draft_for(col: Collection, **kwargs: object) -> CaptureDraft:
    model = col.models.by_name("Basic")
    assert model
    draft = CaptureDraft(
        int(model["id"]), 1, (("Front", "new word"), ("Back", "context"))
    )
    return replace(draft, **kwargs)


def test_capture_previews_source_escapes_text_and_rejects_duplicates(
    col: Collection,
) -> None:
    draft = draft_for(
        col,
        fields=(("Front", "<new word>"), ("Back", "sentence")),
        source_field="Back",
        source_url="https://example.org/lesson",
        source_title="Lesson <1>",
        tags=("capture",),
    )
    count = col.note_count()
    preview = capture_note(col, draft)
    assert preview["Front"] == "&lt;new word&gt;"
    assert "Lesson &lt;1&gt;" in preview["Back"]
    assert "https://example.org/lesson" in preview["Back"]
    assert col.note_count() == count
    add_capture(col, draft)
    with pytest.raises(ValueError, match="duplicates"):
        add_capture(col, draft)
    assert col.note_count() == count + 1
    col.undo()
    assert col.note_count() == count


@pytest.mark.parametrize(
    "url", ["javascript:alert(1)", "file:///tmp/private", "https:relative"]
)
def test_capture_rejects_non_web_sources(col: Collection, url: str) -> None:
    with pytest.raises(ValueError, match="Source URLs"):
        capture_note(col, draft_for(col, source_field="Back", source_url=url))
    assert col.note_count() == 0


def test_capture_detects_audio_change_and_stores_canonical_media(
    col: Collection, tmp_path: Path
) -> None:
    audio = tmp_path / "voice.mp3"
    audio.write_bytes(b"first audio")
    draft = draft_for(
        col,
        audio_field="Back",
        audio_path=str(audio),
        audio_digest=hashlib.sha256(audio.read_bytes()).hexdigest(),
    )
    audio.write_bytes(b"changed audio")
    with pytest.raises(ValueError, match="audio changed"):
        add_capture(col, draft)
    assert col.note_count() == 0
    col.media.write_data("voice.mp3", b"different existing audio")
    draft = replace(draft, audio_digest=hashlib.sha256(audio.read_bytes()).hexdigest())
    add_capture(col, draft)
    note = col.get_note(col.find_notes("new word")[0])
    assert "[sound:voice.mp3]" not in note["Back"]
    stored = note["Back"].split("[sound:", 1)[1].removesuffix("]")
    assert (Path(col.media.dir()) / stored).read_bytes() == audio.read_bytes()


def test_capture_rejects_missing_cloze_and_preserves_valid_cloze(
    col: Collection,
) -> None:
    model = col.models.by_name("Cloze")
    assert model
    fields = tuple(
        (field["name"], "plain text" if index == 0 else "")
        for index, field in enumerate(model["flds"])
    )
    draft = CaptureDraft(int(model["id"]), 1, fields)
    with pytest.raises(ValueError, match="cloze deletions"):
        capture_note(col, draft)
    valid_fields = ((fields[0][0], "Learn {{c1::this term}}."), *fields[1:])
    add_capture(col, replace(draft, fields=valid_fields))
    assert col.card_count() == 1


def test_break_preview_balances_return_load_and_undo_preserves_intervals(
    col: Collection,
) -> None:
    notes = [
        review_note(col, f"card {i}", due) for i, due in enumerate([-2, 0, 1, 2, 2, 3])
    ]
    original = {note.cards()[0].id: note.cards()[0].due for note in notes}
    plan = plan_break(col, "", 0, 2, 2)
    assert plan.before == (2, 1, 2, 1)
    assert plan.after == (0, 0, 3, 3)
    assert len(plan.moves) == 3
    assert {note.cards()[0].id: note.cards()[0].due for note in notes} == original

    apply_break(col, plan)
    assert all(note.cards()[0].ivl == 10 for note in notes)
    assert col.db.scalar("select count(*) from revlog") == 0
    assert plan_break(col, "", 0, 2, 2).before == plan.after
    col.undo()
    assert {note.cards()[0].id: note.cards()[0].due for note in notes} == original


def test_break_rejects_changed_schedule_and_excludes_suspended_cards(
    col: Collection,
) -> None:
    active = review_note(col, "active", 0)
    suspended = review_note(col, "suspended", 0)
    card = suspended.cards()[0]
    card.queue = QUEUE_TYPE_SUSPENDED
    col.update_card(card)
    add_note(col, "new card")
    plan = plan_break(col, "", 0, 2, 2)
    assert len(plan.moves) == 1
    card = active.cards()[0]
    card.due += 1
    col.update_card(card)
    with pytest.raises(ValueError, match="schedule changed"):
        apply_break(col, plan)
    assert active.cards()[0].due == col.sched.today + 1


def test_break_excludes_filtered_and_learning_cards(col: Collection) -> None:
    active = review_note(col, "normal", 0)
    filtered_note = review_note(col, "filtered", 0)
    filtered_deck = col.decks.new_deck_legacy(filtered=True)
    filtered_deck["name"] = "Temporary review"
    did = col.decks.add_deck_legacy(filtered_deck).id
    card = filtered_note.cards()[0]
    card.odid = card.did
    card.odue = card.due
    card.did = DeckId(did)
    col.update_card(card)
    learning_note = add_note(col, "learning")
    learning = learning_note.cards()[0]
    from anki.consts import CARD_TYPE_LRN, QUEUE_TYPE_LRN

    learning.type = CARD_TYPE_LRN
    learning.queue = QUEUE_TYPE_LRN
    learning.due = 123456
    col.update_card(learning)

    plan = plan_break(col, "", 0, 2, 2)
    assert [cid for cid, _due in plan.moves] == [int(active.cards()[0].id)]


def test_retention_comparison_is_read_only_and_validates_inputs(
    col: Collection,
) -> None:
    review_note(col, "simulation", 3)
    with pytest.raises(ValueError, match="Enable upstream FSRS"):
        compare_retention(col, 1, (0.9,), 30)
    col.set_config("fsrs", True)
    before = col.db.all("select * from cards")
    config_before = col.decks.get_config(1)
    undo_before = col.undo_status()
    result = compare_retention(col, 1, (0.8, 0.9), 30)
    assert [row.retention for row in result] == [0.8, 0.9]
    assert all(
        row.reviews >= 0 and row.minutes >= 0 and row.memorized >= 0 for row in result
    )
    assert col.db.all("select * from cards") == before
    assert col.decks.get_config(1) == config_before
    assert col.undo_status() == undo_before
    with pytest.raises(ValueError, match="retention values"):
        compare_retention(col, 1, (float("nan"),), 30)


def test_overview_counts_due_and_repair_cards_without_mutation(col: Collection) -> None:
    note = review_note(col, "overview", 0)
    note.tags = [marker_tag("confusion", int(note.cards()[0].id))]
    col.update_note(note)
    before = NoteSnapshot.read(note)
    summary = next(row for row in deck_summaries(col) if row.deck_id == 1)
    assert summary.due == 1
    assert summary.repairs == 1
    assert summary.minutes == pytest.approx(10 / 60)
    assert NoteSnapshot.read(col.get_note(note.id)) == before
