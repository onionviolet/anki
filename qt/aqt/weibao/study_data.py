# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Collection operations for previewable study tools, without UI dependencies."""

from __future__ import annotations

import hashlib
import html
import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from anki.cards import CardId
from anki.collection import Collection, OpChanges, OpChangesWithCount
from anki.decks import DeckId
from anki.models import NotetypeId
from anki.notes import Note, NoteFieldsCheckResult, NoteId
from anki.scheduler_pb2 import SimulateFsrsReviewRequest
from anki.utils import ids2str

REPAIR_PREFIX = "weibao::repair::"
PROTECT_PREFIX = "weibao::protected::"


def protection_tag(field: str) -> str:
    return PROTECT_PREFIX + field.encode("utf-8").hex()


def protected_fields(note: Note) -> frozenset[str]:
    return frozenset(
        field for field in note.keys() if protection_tag(field) in note.tags
    )


@dataclass(frozen=True)
class NoteSnapshot:
    note_id: int
    model_id: int
    fields: tuple[tuple[str, str], ...]
    tags: tuple[str, ...]

    @classmethod
    def read(cls, note: Note) -> NoteSnapshot:
        return cls(
            int(note.id), int(note.mid), tuple(note.items()), tuple(sorted(note.tags))
        )


@dataclass(frozen=True)
class RepairProposal:
    before: NoteSnapshot
    fields: tuple[tuple[str, str], ...]
    protected: frozenset[str]
    resolved_tags: frozenset[str]


def repair_file(snapshot: NoteSnapshot) -> str:
    return (
        json.dumps(
            {
                "version": 1,
                "note_id": snapshot.note_id,
                "model_id": snapshot.model_id,
                "expected_fields": dict(snapshot.fields),
                "expected_tags": list(snapshot.tags),
                "changes": {},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def import_repair_file(raw: str, snapshot: NoteSnapshot) -> tuple[tuple[str, str], ...]:
    """Proposals carry their exact starting point; import never writes a note."""
    data = json.loads(raw)
    if (
        not isinstance(data, dict)
        or type(data.get("version")) is not int
        or data["version"] != 1
    ):
        raise ValueError("Choose a version 1 repair proposal JSON file.")
    if (
        type(data.get("note_id")) is not int
        or type(data.get("model_id")) is not int
        or data["note_id"] != snapshot.note_id
        or data["model_id"] != snapshot.model_id
        or data.get("expected_fields") != dict(snapshot.fields)
        or data.get("expected_tags") != list(snapshot.tags)
    ):
        raise ValueError(
            "This proposal does not match the loaded note snapshot. Reload or choose the matching note."
        )
    changes = data.get("changes")
    fields = dict(snapshot.fields)
    if (
        not isinstance(changes, dict)
        or not set(changes) <= set(fields)
        or any(not isinstance(value, str) for value in changes.values())
    ):
        raise ValueError("Proposal changes must map existing field names to text.")
    for field, value in changes.items():
        if protection_tag(field) in snapshot.tags and value != fields[field]:
            raise ValueError(f"Unlock {field} before importing changes to it.")
    return tuple((field, changes.get(field, value)) for field, value in snapshot.fields)


def apply_repair(col: Collection, proposal: RepairProposal) -> OpChanges:
    note = col.get_note(NoteId(proposal.before.note_id))
    if NoteSnapshot.read(note) != proposal.before:
        raise ValueError("This note changed after preview. Reload it before accepting.")
    fields = dict(proposal.fields)
    if len(fields) != len(proposal.fields) or set(fields) != set(note.keys()):
        raise ValueError("The proposal must contain each current field exactly once.")
    if not proposal.protected <= set(note.keys()):
        raise ValueError("Unknown protected field.")
    # A protected field must first be unlocked in a separate accepted operation.
    for field in protected_fields(note):
        if fields[field] != note[field]:
            raise ValueError(f"Unlock {field} before changing its contents.")
    if not proposal.resolved_tags <= set(note.tags) or any(
        not tag.startswith(REPAIR_PREFIX) for tag in proposal.resolved_tags
    ):
        raise ValueError("Only existing repair markers can be resolved.")
    for field, value in fields.items():
        note[field] = value
    note.tags = [
        tag
        for tag in note.tags
        if tag not in proposal.resolved_tags and not tag.startswith(PROTECT_PREFIX)
    ]
    note.tags.extend(protection_tag(field) for field in sorted(proposal.protected))
    return col.update_note(note)


def field_diff(
    before: tuple[tuple[str, str], ...], after: tuple[tuple[str, str], ...]
) -> str:
    """Escape note HTML: the comparison is text, never an executable card."""
    original = dict(before)
    rows = []
    for field, value in after:
        if value != original.get(field, ""):
            rows.append(
                f"<h3>{html.escape(field)}</h3><table width='100%'><tr>"
                f"<td width='50%'><pre>{html.escape(original.get(field, ''))}</pre></td>"
                f"<td><pre>{html.escape(value)}</pre></td></tr></table>"
            )
    return "".join(rows)


@dataclass(frozen=True)
class CaptureDraft:
    model_id: int
    deck_id: int
    fields: tuple[tuple[str, str], ...]
    tags: tuple[str, ...] = ()
    source_field: str = ""
    source_url: str = ""
    source_title: str = ""
    audio_field: str = ""
    audio_path: str = ""
    audio_digest: str = ""


def read_audio(path: str) -> bytes:
    file = Path(path)
    if file.suffix.lower() not in {".mp3", ".wav", ".ogg", ".m4a", ".flac"}:
        raise ValueError("Select an MP3, WAV, OGG, M4A or FLAC audio file.")
    if not file.is_file() or file.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("Audio must be a local file of at most 20 MiB.")
    data = file.read_bytes()
    if not data or len(data) > 20 * 1024 * 1024:
        raise ValueError("Audio must be nonempty and at most 20 MiB.")
    return data


def capture_note(col: Collection, draft: CaptureDraft) -> Note:
    model = col.models.get(NotetypeId(draft.model_id))
    deck = col.decks.get(DeckId(draft.deck_id))
    if model is None or deck is None or deck["dyn"]:
        raise ValueError("Choose an existing note type and a normal deck.")
    note = col.new_note(model)
    fields = dict(draft.fields)
    if len(fields) != len(draft.fields) or set(fields) != set(note.keys()):
        raise ValueError("The note type changed. Reload the capture form.")
    for field, text in fields.items():
        # Capture is plain text; preserve cloze braces but not pasted HTML/scripts.
        note[field] = html.escape(text).replace("\n", "<br>")
    if draft.source_url or draft.source_title:
        if draft.source_field not in fields:
            raise ValueError("Choose a field for the source metadata.")
        parsed = urlsplit(draft.source_url)
        if draft.source_url and (
            parsed.scheme not in {"http", "https"} or not parsed.netloc
        ):
            raise ValueError("Source URLs must use http or https.")
        source = "<br>".join(
            html.escape(text) for text in (draft.source_title, draft.source_url) if text
        )
        note[draft.source_field] += (
            "<br>" if note[draft.source_field] else ""
        ) + source
    if draft.audio_path:
        if draft.audio_field not in fields:
            raise ValueError("Choose a field for the audio.")
        read_audio(draft.audio_path)
    if not note.fields[0].strip():
        raise ValueError("The first field must contain text.")
    if any(not tag or any(c.isspace() for c in tag) for tag in draft.tags):
        raise ValueError("Separate tags with spaces.")
    note.tags = list(draft.tags)
    state = note.fields_check()
    if state in (NoteFieldsCheckResult.EMPTY, NoteFieldsCheckResult.DUPLICATE):
        raise ValueError("The first field is empty or duplicates an existing note.")
    if state != NoteFieldsCheckResult.NORMAL:
        raise ValueError(
            "Check the cloze deletions and the chosen note type before adding this note."
        )
    return note


def add_capture(col: Collection, draft: CaptureDraft) -> OpChangesWithCount:
    note = capture_note(col, draft)
    if draft.audio_path:
        data = read_audio(draft.audio_path)
        if hashlib.sha256(data).hexdigest() != draft.audio_digest:
            raise ValueError("The audio changed after preview. Preview again.")
        # The media manager deduplicates and returns the canonical stored name.
        name = col.media.write_data(Path(draft.audio_path).name, data)
        note[draft.audio_field] += f"[sound:{name}]"
    return col.add_note(note, DeckId(draft.deck_id))


@dataclass(frozen=True)
class DueCard:
    card_id: int
    due: int
    state: bytes


@dataclass(frozen=True)
class BreakPlan:
    search: str
    today: int
    cards: tuple[DueCard, ...]
    moves: tuple[tuple[int, int], ...]
    before: tuple[int, ...]
    after: tuple[int, ...]


def due_cards(col: Collection, search: str) -> tuple[DueCard, ...]:
    ids = col.find_cards(
        f"({search}) is:review -is:suspended -is:buried -deck:filtered"
        if search
        else "is:review -is:suspended -is:buried -deck:filtered"
    )
    if len(ids) > 10000:
        raise ValueError("Narrow the search to at most 10,000 review cards.")
    cards = []
    for cid in ids:
        card = col.get_card(cid)
        if card.queue == 2 and card.type == 2 and not card.odid:
            cards.append(
                DueCard(int(cid), card.due, card._to_backend_card().SerializeToString())
            )
    return tuple(sorted(cards, key=lambda card: card.card_id))


def plan_break(
    col: Collection, search: str, start: int, days: int, spread: int
) -> BreakPlan:
    if not 0 <= start <= 60 or not 1 <= days <= 30 or not 1 <= spread <= 60:
        raise ValueError(
            "Choose a start within 60 days, a 1–30 day break, and a 1–60 day return period."
        )
    today = col.sched.today
    cards = due_cards(col, search)
    end = start + days
    horizon = end + spread
    before = [0] * horizon
    after = [0] * horizon
    affected = []
    for card in cards:
        day = max(0, card.due - today)
        if day < horizon:
            before[day] += 1
        if start <= day < end:
            affected.append(card)
        elif day < horizon:
            after[day] += 1
    moves = []
    for card in sorted(affected, key=lambda card: (card.due, card.card_id)):
        target = min(range(end, horizon), key=lambda day: (after[day], day))
        after[target] += 1
        moves.append((card.card_id, today + target))
    return BreakPlan(search, today, cards, tuple(moves), tuple(before), tuple(after))


def apply_break(col: Collection, plan: BreakPlan) -> OpChanges:
    if col.sched.today != plan.today or due_cards(col, plan.search) != plan.cards:
        raise ValueError(
            "The schedule changed after preview. Preview again before applying."
        )
    if not plan.moves:
        raise ValueError("No review cards fall during this break.")
    cards = []
    for cid, due in plan.moves:
        card = col.get_card(CardId(cid))
        card.due = due
        cards.append(card)
    # One collection operation gives an atomic write and one standard undo entry.
    # Review history, intervals and FSRS memory states are preserved.
    return col.update_cards(cards)


@dataclass(frozen=True)
class DeckSummary:
    deck_id: int
    name: str
    due: int
    minutes: float
    repairs: int


def deck_summaries(col: Collection) -> list[DeckSummary]:
    due_ids = col.find_cards("is:due -is:suspended -is:buried -deck:filtered")
    due: dict[int, int] = {
        int(did): int(count)
        for did, count in col.db.all(
            f"select did, count(*) from cards where id in {ids2str(due_ids)} group by did"
        )
    }
    # A marker names an exact card; do not count all its siblings as repairs.
    repairs: Counter[int] = Counter()
    for nid in col.find_notes("tag:weibao::repair::*"):
        note = col.get_note(nid)
        marked = set()
        for tag in note.tags:
            if tag.startswith(REPAIR_PREFIX):
                tail = tag.rsplit("::card_", 1)
                if len(tail) == 2 and tail[1].isdigit():
                    marked.add(int(tail[1]))
        for cid, did in col.db.all("select id, did from cards where nid=?", nid):
            if cid in marked:
                repairs[did] += 1
    # Review time is a collection-wide historical average, not a promise.
    average_ms = col.db.scalar("select avg(min(time, 60000)) from revlog where type=1")
    seconds = float(average_ms) / 1000 if average_ms is not None else 10.0
    return [
        DeckSummary(
            int(deck.id),
            deck.name,
            due.get(deck.id, 0),
            due.get(deck.id, 0) * seconds / 60,
            repairs[deck.id],
        )
        for deck in col.decks.all_names_and_ids(include_filtered=False)
    ]


@dataclass(frozen=True)
class RetentionResult:
    retention: float
    reviews: float
    minutes: float
    memorized: float


def compare_retention(
    col: Collection, deck_id: int, retentions: tuple[float, ...], days: int
) -> list[RetentionResult]:
    if (
        not 1 <= len(retentions) <= 5
        or any(not math.isfinite(r) or not 0.7 <= r <= 0.99 for r in retentions)
        or not 30 <= days <= 365
    ):
        raise ValueError(
            "Compare 1–5 retention values from 0.70 to 0.99 over 30–365 days."
        )
    deck = col.decks.get(DeckId(deck_id))
    if deck is None or deck["dyn"]:
        raise ValueError("Choose a normal deck.")
    data = col.decks.get_deck_configs_for_update(DeckId(deck_id))
    if not data.fsrs:
        raise ValueError(
            "Enable upstream FSRS in deck options before comparing retention."
        )
    config = next(
        item.config.config
        for item in data.all_config
        if item.config.id == data.current_deck.config_id
    )
    search = f"did:{deck_id} -is:suspended -is:buried"
    size = len(col.find_cards(search))
    if not size:
        raise ValueError("The selected deck has no active cards.")
    results = []
    for retention in retentions:
        request = SimulateFsrsReviewRequest(
            params=list(
                config.fsrs_params_6 or config.fsrs_params_5 or config.fsrs_params_4
            ),
            desired_retention=retention,
            # Backend deck_size means additional unseen cards beyond the cards
            # returned by search. Simulate only the selected existing collection.
            deck_size=0,
            days_to_simulate=days,
            new_limit=config.new_per_day,
            review_limit=config.reviews_per_day,
            max_interval=config.maximum_review_interval,
            search=search,
            new_cards_ignore_review_limit=data.new_cards_ignore_review_limit,
            easy_days_percentages=list(config.easy_days_percentages),
            review_order=config.review_order,
            historical_retention=config.historical_retention,
            learning_step_count=len(config.learn_steps),
            relearning_step_count=len(config.relearn_steps),
        )
        if config.leech_action == 0:
            request.suspend_after_lapse_count = config.leech_threshold
        output = col._backend.simulate_fsrs_review(request)
        results.append(
            RetentionResult(
                retention,
                sum(output.daily_review_count) / days,
                sum(output.daily_time_cost) / days / 60,
                output.accumulated_knowledge_acquisition[-1]
                if output.accumulated_knowledge_acquisition
                else 0.0,
            )
        )
    return results
