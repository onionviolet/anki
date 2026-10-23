# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Last-minute cramming: flip and swipe through cards without scheduling."""

from __future__ import annotations

import html
import json
import random
import re
from collections import deque
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from anki.collection import SearchNode
from aqt.deckbrowser import DeckBrowser, DeckBrowserContent
from aqt.qt import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QKeySequence,
    QLabel,
    QPushButton,
    QShortcut,
    Qt,
    QVBoxLayout,
    qconnect,
)
from aqt.sound import play_clicked_audio
from aqt.utils import tr
from aqt.webview import AnkiWebView

if TYPE_CHECKING:
    from anki.cards import Card, CardId
    from aqt.main import AnkiQt

ANSWER_SPLIT = re.compile(r"<hr id=['\"]?answer['\"]?>", re.IGNORECASE)


class CramSession:
    """Queue state for one pass. Never touches card scheduling.

    "known" cards leave the queue; "again" cards go to the back, so the pass
    ends only once every card has been marked known.
    """

    def __init__(self, card_ids: Sequence[CardId], shuffle: bool = True) -> None:
        ids = list(card_ids)
        if shuffle:
            random.shuffle(ids)
        self.total = len(ids)
        self.queue: deque[CardId] = deque(ids)
        self.known = 0
        self.missed: set[CardId] = set()
        self._history: list[tuple[CardId, bool]] = []

    @property
    def current(self) -> CardId | None:
        return self.queue[0] if self.queue else None

    @property
    def done(self) -> bool:
        return not self.queue

    def mark_known(self) -> None:
        if cid := self.current:
            self.queue.popleft()
            self.known += 1
            self._history.append((cid, True))

    def mark_again(self) -> None:
        if cid := self.current:
            self.queue.rotate(-1)
            self.missed.add(cid)
            self._history.append((cid, False))

    def undo(self) -> bool:
        if not self._history:
            return False
        cid, was_known = self._history.pop()
        if was_known:
            self.queue.appendleft(cid)
            self.known -= 1
        else:
            self.queue.rotate(1)
        return True


def split_sides(question: str, answer: str) -> tuple[str, str]:
    "Answer html repeats the question above <hr id=answer>; show only the back."
    parts = ANSWER_SPLIT.split(answer, maxsplit=1)
    return question, parts[1] if len(parts) == 2 else answer


CRAM_HTML = """
<div id="cram-wrap"><div id="qa" class="card" dir="auto"></div></div>
<style>
html, body { height: 100%; overflow: hidden; }
#cram-wrap { height: 100%; display: flex; align-items: center;
  justify-content: center; overflow-y: auto; touch-action: pan-y;
  user-select: none; }
#qa { max-width: 100%; transition: transform .18s ease, opacity .18s ease; }
#qa.off-right { transform: translateX(120%) rotate(8deg); opacity: 0; }
#qa.off-left { transform: translateX(-120%) rotate(-8deg); opacity: 0; }
#qa.enter { transition: none; opacity: 0; }
</style>
<script>
var cramStart = null, cramDx = 0;
function cramShow(html, cls) {
  var qa = document.getElementById("qa");
  qa.className = "card enter " + cls;
  qa.style.transform = "";
  qa.innerHTML = html;
  void qa.offsetWidth;
  qa.className = "card " + cls;
  qa.style.opacity = 1;
  document.getElementById("cram-wrap").scrollTop = 0;
}
function cramFly(dir) {
  var qa = document.getElementById("qa");
  qa.style.transform = "";
  qa.classList.add(dir > 0 ? "off-right" : "off-left");
  setTimeout(function() { pycmd(dir > 0 ? "cram:known" : "cram:again"); }, 150);
}
document.addEventListener("pointerdown", function(e) {
  if (e.target.closest("a, button, input, [onclick]")) { return; }
  cramStart = e.clientX; cramDx = 0;
});
document.addEventListener("pointermove", function(e) {
  if (cramStart === null) { return; }
  cramDx = e.clientX - cramStart;
  var qa = document.getElementById("qa");
  qa.style.transition = "none";
  qa.style.transform = "translateX(" + cramDx + "px) rotate(" + (cramDx / 40) + "deg)";
});
document.addEventListener("pointerup", function() {
  if (cramStart === null) { return; }
  var dx = cramDx, qa = document.getElementById("qa");
  cramStart = null;
  qa.style.transition = "";
  if (Math.abs(dx) > 110) { cramFly(dx); return; }
  qa.style.transform = "";
  if (Math.abs(dx) < 6) { pycmd("cram:flip"); }
});
</script>
"""


class CramDialog(QDialog):
    def __init__(self, mw: AnkiQt) -> None:
        super().__init__(mw)
        self.mw = mw
        self.setWindowTitle(tr.weibao_cram_mode())
        self.resize(760, 640)
        self.session: CramSession | None = None
        self.card: Card | None = None
        self.showing_answer = False
        self._web_ready = False

        self.deck = QComboBox()
        self.deck.addItem(tr.weibao_cram_all_decks(), 0)
        for entry in mw.col.decks.all_names_and_ids(include_filtered=False):
            self.deck.addItem(entry.name, entry.id)
        if (idx := self.deck.findData(mw.col.decks.get_current_id())) >= 0:
            self.deck.setCurrentIndex(idx)
        self.shuffle = QCheckBox(tr.weibao_cram_shuffle())
        self.shuffle.setChecked(True)
        self.restart_button = QPushButton(tr.weibao_cram_restart())
        self.progress = QLabel()

        top = QHBoxLayout()
        top.addWidget(self.deck, 1)
        top.addWidget(self.shuffle)
        top.addWidget(self.restart_button)

        self.web = AnkiWebView(parent=self, title="cram mode")
        self.web.set_bridge_command(self._on_bridge, self)
        self.web.stdHtml(CRAM_HTML, css=["css/reviewer.css"], js=[], context=self)

        self.again_button = QPushButton(tr.weibao_cram_still_learning())
        self.flip_button = QPushButton(tr.weibao_cram_flip())
        self.known_button = QPushButton(tr.weibao_cram_know_it())
        self.undo_button = QPushButton(tr.weibao_cram_undo())
        bottom = QHBoxLayout()
        for button in (
            self.undo_button,
            self.again_button,
            self.flip_button,
            self.known_button,
        ):
            bottom.addWidget(button)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.progress)
        layout.addWidget(self.web, 1)
        layout.addLayout(bottom)

        qconnect(self.restart_button.clicked, self.restart)
        qconnect(self.deck.currentIndexChanged, lambda _i: self.restart())
        qconnect(self.again_button.clicked, self.again)
        qconnect(self.known_button.clicked, self.known)
        qconnect(self.flip_button.clicked, self.flip)
        qconnect(self.undo_button.clicked, self.undo)
        for keys, func in (
            (("Left",), self.again),
            (("Right",), self.known),
            (("Space", "Up", "Down"), self.flip),
            (("Z",), self.undo),
        ):
            for key in keys:
                shortcut = QShortcut(QKeySequence(key), self)
                shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
                qconnect(shortcut.activated, func)

        self.restart()

    # session control
    ######################################################################

    def restart(self) -> None:
        deck_id = self.deck.currentData()
        nodes = [SearchNode(deck=self.deck.currentText())] if deck_id else []
        search = self.mw.col.build_search_string(*nodes) if nodes else ""
        ids = self.mw.col.find_cards(f"{search} -is:suspended".strip())
        self.session = CramSession(ids, shuffle=self.shuffle.isChecked())
        self._show_current()

    def known(self) -> None:
        self._advance(True)

    def again(self) -> None:
        self._advance(False)

    def _advance(self, known: bool) -> None:
        if not self.session or self.session.done:
            return
        if known:
            self.session.mark_known()
        else:
            self.session.mark_again()
        self._show_current()

    def undo(self) -> None:
        if self.session and self.session.undo():
            self._show_current()

    def flip(self) -> None:
        if self.card is None or self.session is None or self.session.done:
            return
        self.showing_answer = not self.showing_answer
        self._render()

    # rendering
    ######################################################################

    def _show_current(self) -> None:
        session = self.session
        assert session is not None
        self.showing_answer = False
        cid = session.current
        self.card = self.mw.col.get_card(cid) if cid else None
        for button in (self.again_button, self.known_button, self.flip_button):
            button.setEnabled(self.card is not None)
        self.undo_button.setEnabled(bool(session._history))
        self.progress.setText(
            tr.weibao_cram_progress(
                known=str(session.known),
                total=session.total,
                missed=str(len(session.missed)),
            )
        )
        self._render()

    def _render(self) -> None:
        if self.card is None:
            assert self.session is not None
            html_text = (
                f"<h2>{tr.weibao_cram_done()}</h2>"
                if self.session.total
                else f"<h2>{tr.weibao_cram_empty()}</h2>"
            )
            cls = ""
        else:
            front, back = split_sides(self.card.question(), self.card.answer())
            text = back if self.showing_answer else front
            html_text = self.card.css() + self.mw.prepare_card_text_for_display(text)
            cls = f"card{self.card.ord + 1}"
        self.web.eval(f"cramShow({json.dumps(html_text)}, {json.dumps(cls)});")

    def _on_bridge(self, cmd: str) -> bool:
        if cmd == "cram:flip":
            self.flip()
        elif cmd == "cram:known":
            self.known()
        elif cmd == "cram:again":
            self.again()
        elif cmd.startswith("play:") and self.card:
            play_clicked_audio(cmd, self.card)
        return False

    def reject(self) -> None:
        self.web.cleanup()
        super().reject()


def install(mw: AnkiQt) -> None:
    dialog: CramDialog | None = None

    def show() -> None:
        nonlocal dialog
        if mw.col is None:
            return
        if dialog is None:
            dialog = CramDialog(mw)
            qconnect(dialog.finished, closed)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def closed(_result: int) -> None:
        nonlocal dialog
        dialog = None

    from aqt import gui_hooks

    def close_profile() -> None:
        if dialog:
            dialog.close()

    action = mw.form.menuTools.addAction(tr.weibao_cram_mode())
    action.setShortcut(QKeySequence("Ctrl+Shift+K"))
    qconnect(action.triggered, show)
    gui_hooks.profile_will_close.append(close_profile)

    def home_entry(_browser: DeckBrowser, content: DeckBrowserContent) -> None:
        label = html.escape(tr.weibao_cram_mode())
        content.stats += f"<p><button type='button' onclick=\"pycmd('weibao:cram-mode')\">{label}</button></p>"

    def bridge(
        handled: tuple[bool, Any], message: str, context: Any
    ) -> tuple[bool, Any]:
        if (
            not handled[0]
            and message == "weibao:cram-mode"
            and isinstance(context, DeckBrowser)
        ):
            show()
            return True, None
        return handled

    gui_hooks.deck_browser_will_render_content.append(home_entry)
    gui_hooks.webview_did_receive_js_message.append(bridge)
