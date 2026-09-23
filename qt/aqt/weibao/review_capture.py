# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Capture repair reasons from the reviewer without changing scheduling."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aqt import gui_hooks
from aqt.operations.tag import add_tags_to_notes
from aqt.qt import QMenu

if TYPE_CHECKING:
    from aqt.reviewer import Reviewer

REASONS = (
    ("Bad explanation", "explanation"),
    ("Confused with another card", "confusion"),
)


def marker_tag(reason: str, card_id: int) -> str:
    """Keep the reason and exact card identity in a syncable note tag."""
    if reason not in {code for _, code in REASONS}:
        raise ValueError(f"unknown review marker: {reason}")
    return f"weibao::repair::{reason}::card_{card_id}"


def mark_for_repair(reviewer: Reviewer, reason: str) -> None:
    card = reviewer.card
    if card is None:
        return
    add_tags_to_notes(
        parent=reviewer.mw,
        note_ids=[card.nid],
        space_separated_tags=marker_tag(reason, int(card.id)),
    ).run_in_background()


def add_review_menu(reviewer: Reviewer, menu: QMenu) -> None:
    if reviewer.card is None:
        return
    repair_menu = menu.addMenu("Mark for repair")
    for label, reason in REASONS:
        action = repair_menu.addAction(label)
        action.triggered.connect(
            lambda _checked=False, reason=reason: mark_for_repair(reviewer, reason)
        )


def install() -> None:
    gui_hooks.reviewer_will_show_context_menu.append(add_review_menu)
