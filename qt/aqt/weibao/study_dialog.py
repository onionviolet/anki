# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Native study dashboard and explicit preview/accept flows."""

from __future__ import annotations

import hashlib
import html
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aqt
from anki.collection import Collection, OpChanges
from anki.models import NotetypeId
from anki.notes import NoteId
from aqt import gui_hooks
from aqt.deckbrowser import DeckBrowser, DeckBrowserContent
from aqt.deckoptions import display_options_for_deck_id
from aqt.operations import CollectionOp, QueryOp
from aqt.qt import (
    QByteArray,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    qconnect,
)
from aqt.sound import av_player
from aqt.utils import openLink, showWarning, tr

from .study_data import (
    BreakPlan,
    CaptureDraft,
    DeckSummary,
    NoteSnapshot,
    RepairProposal,
    RetentionResult,
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
    read_audio,
    repair_file,
)

if TYPE_CHECKING:
    from aqt.main import AnkiQt


class NumberItem(QTableWidgetItem):
    def __init__(self, value: float, *, decimals: int = 0) -> None:
        super().__init__(f"{value:.{decimals}f}")
        self.setData(Qt.ItemDataRole.UserRole, value)

    def __lt__(self, other: QTableWidgetItem) -> bool:
        return float(self.data(Qt.ItemDataRole.UserRole)) < float(
            other.data(Qt.ItemDataRole.UserRole)
        )


def table(headers: list[str]) -> QTableWidget:
    widget = QTableWidget(0, len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    widget.horizontalHeader().setSectionsMovable(True)
    widget.resizeColumnsToContents()
    return widget


class StudyDialog(QDialog):
    def __init__(self, mw: AnkiQt) -> None:
        super().__init__(mw)
        self.mw = mw
        self._closed = False
        self._versions: dict[str, int] = {}
        self._busy = False
        self._snapshot: NoteSnapshot | None = None
        self._proposal: RepairProposal | None = None
        self._draft: CaptureDraft | None = None
        self._plan: BreakPlan | None = None
        self._repair_fields: dict[str, tuple[QTextEdit, QCheckBox]] = {}
        self._capture_fields: dict[str, QTextEdit] = {}
        self._models: dict[int, tuple[str, ...]] = {}
        self._audio_path = ""
        self.setWindowTitle(tr.weibao_study_tools())
        self.resize(950, 720)
        self.setMinimumSize(600, 450)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self._overview_tab()
        self._repair_tab()
        self._capture_tab()
        self._break_tab()
        self._retention_tab()
        links = QHBoxLayout()
        links.addWidget(QLabel(tr.weibao_integrations()))
        for title, url in (
            (tr.weibao_yomitan(), "https://yomitan.wiki/anki/"),
            (
                tr.weibao_hypertts(),
                "https://github.com/Vocab-Apps/anki-hyper-tts",
            ),
            (
                tr.weibao_fsrs_helper(),
                "https://github.com/open-spaced-repetition/fsrs4anki-helper",
            ),
        ):
            button = QPushButton(title)
            qconnect(button.clicked, lambda _checked=False, url=url: openLink(url))
            links.addWidget(button)
        layout.addLayout(links)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        qconnect(buttons.rejected, self.close)
        layout.addWidget(buttons)
        qconnect(self.finished, self._finish)
        gui_hooks.operation_did_execute.append(self._operation_did_execute)
        self.refresh_overview()
        self.refresh_repairs()
        self._query(self._capture_setup, self._load_setup, "setup")

    def _tab(self, title: str, help_text: str, *, scroll: bool = False) -> QVBoxLayout:
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel(help_text)
        label.setWordWrap(True)
        layout.addWidget(label)
        if scroll:
            # Capture has fields, metadata, audio and preview controls. Preserve
            # their minimum sizes instead of squeezing form rows into each other.
            layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
            area = QScrollArea()
            area.setWidgetResizable(True)
            area.setWidget(page)
            self.tabs.addTab(area, title)
        else:
            self.tabs.addTab(page, title)
        return layout

    def _button(
        self, layout: QVBoxLayout | QHBoxLayout, text: str, callback: Callable[[], None]
    ) -> QPushButton:
        button = QPushButton(text)
        qconnect(button.clicked, callback)
        layout.addWidget(button)
        return button

    def _invalidate(self, key: str) -> None:
        self._versions[key] = self._versions.get(key, 0) + 1
        if key == "repair":
            self._proposal = None
            self.repair_accept.setEnabled(False)
        elif key == "capture":
            self._draft = None
            self.capture_accept.setEnabled(False)
        elif key == "break":
            self._plan = None
            self.break_accept.setEnabled(False)

    def _query(
        self, op: Callable[[Collection], Any], success: Callable[[Any], None], key: str
    ) -> None:
        self._versions[key] = version = self._versions.get(key, 0) + 1

        def ready(result: Any) -> None:
            if not self._closed and self._versions.get(key) == version:
                success(result)

        def failed(error: Exception) -> None:
            if not self._closed and self._versions.get(key) == version:
                showWarning(str(error), parent=self)

        QueryOp(parent=self.mw, op=op, success=ready).failure(
            failed
        ).with_progress().run_in_background()

    def _mutate(self, op: Callable[[Collection], Any], key: str) -> None:
        if self._busy:
            return
        self._busy = True
        self.tabs.setEnabled(False)

        def finished(_result: Any) -> None:
            self._busy = False
            if self._closed:
                return
            self.tabs.setEnabled(True)
            self.status.setText(tr.weibao_saved())
            self._invalidate(key)
            self.refresh_overview()
            if key == "repair":
                self.refresh_repairs()

        def failed(error: Exception) -> None:
            self._busy = False
            if not self._closed:
                self.tabs.setEnabled(True)
                showWarning(str(error), parent=self)

        CollectionOp(self.mw, op).success(finished).failure(failed).run_in_background(
            initiator=self
        )

    def _operation_did_execute(
        self, changes: OpChanges, handler: object | None
    ) -> None:
        if not self._closed and handler is not self:
            self.refresh_overview()

    def _overview_tab(self) -> None:
        layout = self._tab(tr.weibao_overview(), tr.weibao_overview_help())
        self.overview = table(
            [
                tr.weibao_deck(),
                tr.weibao_due(),
                tr.weibao_minutes(),
                tr.weibao_repair_cards(),
            ]
        )
        self.overview.setSortingEnabled(True)
        state = self.mw.pm.profile.get("weibao_study_columns", "")
        if isinstance(state, str) and state:
            self.overview.horizontalHeader().restoreState(
                QByteArray.fromHex(state.encode())
            )
        layout.addWidget(self.overview)
        qconnect(self.overview.cellDoubleClicked, self._browse_deck)
        self._button(layout, tr.weibao_refresh(), self.refresh_overview)

    def refresh_overview(self) -> None:
        self._query(deck_summaries, self._show_overview, "overview")

    def _show_overview(self, rows: list[DeckSummary]) -> None:
        self.overview.setSortingEnabled(False)
        self.overview.setRowCount(len(rows))
        for row, deck in enumerate(rows):
            name = QTableWidgetItem(deck.name)
            name.setData(Qt.ItemDataRole.UserRole, deck.deck_id)
            self.overview.setItem(row, 0, name)
            self.overview.setItem(row, 1, NumberItem(deck.due))
            self.overview.setItem(row, 2, NumberItem(deck.minutes, decimals=1))
            self.overview.setItem(row, 3, NumberItem(deck.repairs))
        self.overview.setSortingEnabled(True)
        self.overview.resizeColumnsToContents()

    def _browse_deck(self, row: int, _column: int) -> None:
        item = self.overview.item(row, 0)
        if item:
            aqt.dialogs.open(
                "Browser",
                self.mw,
                search=(f"did:{int(item.data(Qt.ItemDataRole.UserRole))}",),
            )

    def _repair_tab(self) -> None:
        layout = self._tab(tr.weibao_repairs(), tr.weibao_repair_help())
        self.repair_notes = QComboBox()
        self.repair_notes.setAccessibleName(tr.weibao_note())
        layout.addWidget(self.repair_notes)
        qconnect(self.repair_notes.currentIndexChanged, self._load_repair)
        self.repair_scroll = QScrollArea()
        self.repair_scroll.setWidgetResizable(True)
        layout.addWidget(self.repair_scroll)
        self.resolve = QCheckBox(tr.weibao_resolve())
        self.resolve.setChecked(True)
        qconnect(self.resolve.toggled, lambda: self._invalidate("repair"))
        layout.addWidget(self.resolve)
        self.repair_preview = QTextBrowser()
        self.repair_preview.setOpenExternalLinks(False)
        layout.addWidget(self.repair_preview)
        files = QHBoxLayout()
        self._button(files, tr.weibao_export_snapshot(), self._export_repair)
        self._button(files, tr.weibao_import_proposal(), self._import_repair)
        layout.addLayout(files)
        actions = QHBoxLayout()
        self._button(actions, tr.weibao_refresh(), self.refresh_repairs)
        self._button(actions, tr.weibao_preview(), self._preview_repair)
        self.repair_accept = self._button(
            actions, tr.weibao_accept_repair(), self._accept_repair
        )
        self.repair_accept.setEnabled(False)
        layout.addLayout(actions)

    def refresh_repairs(self) -> None:
        self._invalidate("repair")
        self._snapshot = None
        self._query(
            lambda col: [
                (int(nid), col.get_note(nid).fields[0][:100])
                for nid in col.find_notes("tag:weibao::repair::*")
            ],
            self._show_repairs,
            "repairs",
        )

    def _show_repairs(self, rows: list[tuple[int, str]]) -> None:
        self.repair_notes.clear()
        for nid, text in rows:
            self.repair_notes.addItem(f"{nid}: {text}", nid)
        if not rows:
            self.repair_scroll.setWidget(QWidget())
            self.repair_preview.setPlainText(tr.weibao_no_repairs())

    def _load_repair(self, _index: int) -> None:
        self._invalidate("repair")
        self._snapshot = None
        nid = self.repair_notes.currentData()
        if nid is not None:
            self._query(
                lambda col: (
                    NoteSnapshot.read(col.get_note(NoteId(nid))),
                    protected_fields(col.get_note(NoteId(nid))),
                ),
                self._show_repair,
                "repair",
            )

    def _show_repair(self, data: tuple[NoteSnapshot, frozenset[str]]) -> None:
        self._snapshot, protected = data
        widget = QWidget()
        form = QFormLayout(widget)
        self._repair_fields = {}
        self.repair_preview.clear()
        for field, value in self._snapshot.fields:
            edit = QTextEdit()
            edit.setPlainText(value)
            edit.setAccessibleName(field)
            edit.setMaximumHeight(100)
            edit.setReadOnly(field in protected)
            lock = QCheckBox(tr.weibao_protect())
            lock.setAccessibleName(f"{field}: {tr.weibao_protect()}")
            lock.setChecked(field in protected)
            qconnect(edit.textChanged, lambda: self._invalidate("repair"))
            qconnect(lock.toggled, lambda: self._invalidate("repair"))
            form.addRow(field, edit)
            form.addRow("", lock)
            self._repair_fields[field] = (edit, lock)
        self.repair_scroll.setWidget(widget)

    def _preview_repair(self) -> None:
        if self._snapshot is None:
            return
        fields = tuple(
            (
                field,
                edit.toPlainText()
                if edit.document().isModified()
                else dict(self._snapshot.fields)[field],
            )
            for field, (edit, _lock) in self._repair_fields.items()
        )
        protected = frozenset(
            field
            for field, (_edit, lock) in self._repair_fields.items()
            if lock.isChecked()
        )
        markers = (
            frozenset(
                tag for tag in self._snapshot.tags if tag.startswith("weibao::repair::")
            )
            if self.resolve.isChecked()
            else frozenset()
        )
        self._proposal = RepairProposal(self._snapshot, fields, protected, markers)
        diff = field_diff(self._snapshot.fields, fields) or html.escape(
            tr.weibao_preview_empty()
        )
        summary = tr.weibao_protection_preview(
            fields=", ".join(sorted(protected)) or tr.weibao_none(), count=len(markers)
        )
        self.repair_preview.setHtml(diff + f"<p>{html.escape(summary)}</p>")
        self.repair_accept.setEnabled(True)

    def _accept_repair(self) -> None:
        if proposal := self._proposal:
            self._mutate(lambda col: apply_repair(col, proposal), "repair")

    def _export_repair(self) -> None:
        if self._snapshot is None:
            return
        path, _filter = QFileDialog.getSaveFileName(
            self,
            tr.weibao_export_snapshot(),
            str(Path.home() / f"repair-{self._snapshot.note_id}.json"),
            "JSON (*.json)",
        )
        if path:
            try:
                Path(path).write_text(repair_file(self._snapshot), encoding="utf-8")
            except OSError as error:
                showWarning(str(error), parent=self)

    def _import_repair(self) -> None:
        if self._snapshot is None:
            return
        path, _filter = QFileDialog.getOpenFileName(
            self, tr.weibao_import_proposal(), "", "JSON (*.json)"
        )
        if not path:
            return
        try:
            file = Path(path)
            if file.stat().st_size > 1024 * 1024:
                raise ValueError("Repair proposal files must be at most 1 MiB.")
            fields = import_repair_file(
                file.read_text(encoding="utf-8"), self._snapshot
            )
        except (OSError, ValueError) as error:
            showWarning(str(error), parent=self)
            return
        for field, value in fields:
            edit = self._repair_fields[field][0]
            edit.setPlainText(value)
            edit.document().setModified(value != dict(self._snapshot.fields)[field])
        self._preview_repair()

    def _capture_tab(self) -> None:
        layout = self._tab(tr.weibao_capture(), tr.weibao_capture_help(), scroll=True)
        form = QFormLayout()
        self.capture_deck = QComboBox()
        self.capture_model = QComboBox()
        form.addRow(tr.weibao_deck(), self.capture_deck)
        form.addRow(tr.weibao_note_type(), self.capture_model)
        qconnect(
            self.capture_deck.currentIndexChanged, lambda: self._invalidate("capture")
        )
        qconnect(self.capture_model.currentIndexChanged, self._capture_model_changed)
        layout.addLayout(form)
        self.capture_scroll = QScrollArea()
        self.capture_scroll.setWidgetResizable(True)
        self.capture_scroll.setMinimumHeight(180)
        layout.addWidget(self.capture_scroll)
        metadata = QFormLayout()
        self.source_url = QLineEdit()
        self.source_title = QLineEdit()
        self.source_field = QComboBox()
        self.audio_field = QComboBox()
        self.capture_tags = QLineEdit()
        for label, widget in (
            (tr.weibao_source_url(), self.source_url),
            (tr.weibao_source_title(), self.source_title),
            (tr.weibao_source_field(), self.source_field),
            (tr.weibao_audio_field(), self.audio_field),
            (tr.weibao_tags(), self.capture_tags),
        ):
            metadata.addRow(label, widget)
            if isinstance(widget, QLineEdit):
                qconnect(widget.textChanged, lambda: self._invalidate("capture"))
            else:
                qconnect(
                    widget.currentIndexChanged, lambda: self._invalidate("capture")
                )
        layout.addLayout(metadata)
        audio = QHBoxLayout()
        self._button(audio, tr.weibao_audio_file(), self._choose_audio)
        self._button(audio, tr.weibao_play_audio(), self._play_audio)
        self._button(audio, tr.weibao_clear_audio(), self._clear_audio)
        self.audio_label = QLabel(tr.weibao_no_audio())
        audio.addWidget(self.audio_label)
        layout.addLayout(audio)
        self.capture_preview = QTextBrowser()
        self.capture_preview.setOpenExternalLinks(False)
        self.capture_preview.setMaximumHeight(100)
        layout.addWidget(self.capture_preview)
        actions = QHBoxLayout()
        self._button(actions, tr.weibao_preview(), self._preview_capture)
        self.capture_accept = self._button(
            actions, tr.weibao_add_note(), self._accept_capture
        )
        self.capture_accept.setEnabled(False)
        layout.addLayout(actions)

    @staticmethod
    def _capture_setup(
        col: Collection,
    ) -> tuple[list[tuple[int, str]], list[tuple[int, str, tuple[str, ...]]]]:
        decks = [
            (int(deck.id), deck.name)
            for deck in col.decks.all_names_and_ids(include_filtered=False)
        ]
        models = []
        for name in col.models.all_names_and_ids():
            model = col.models.get(NotetypeId(name.id))
            if model:
                models.append(
                    (
                        int(name.id),
                        name.name,
                        tuple(field["name"] for field in model["flds"]),
                    )
                )
        return decks, models

    def _load_setup(
        self, data: tuple[list[tuple[int, str]], list[tuple[int, str, tuple[str, ...]]]]
    ) -> None:
        decks, models = data
        for did, name in decks:
            self.capture_deck.addItem(name, did)
            self.retention_deck.addItem(name, did)
        for mid, name, fields in models:
            self._models[mid] = fields
            self.capture_model.addItem(name, mid)

    def _capture_model_changed(self, _index: int) -> None:
        self._invalidate("capture")
        fields = self._models.get(self.capture_model.currentData(), ())
        widget = QWidget()
        form = QFormLayout(widget)
        self._capture_fields = {}
        for combo in (self.source_field, self.audio_field):
            combo.clear()
            combo.addItem(tr.weibao_none(), "")
            for field in fields:
                combo.addItem(field, field)
        for field in fields:
            edit = QTextEdit()
            edit.setAccessibleName(field)
            edit.setMaximumHeight(90)
            qconnect(edit.textChanged, lambda: self._invalidate("capture"))
            form.addRow(field, edit)
            self._capture_fields[field] = edit
        self.capture_scroll.setWidget(widget)

    def _choose_audio(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self, tr.weibao_audio_file(), "", "Audio (*.mp3 *.wav *.ogg *.m4a *.flac)"
        )
        if path:
            self._audio_path = path
            self.audio_label.setText(Path(path).name)
            self._invalidate("capture")

    def _play_audio(self) -> None:
        if self._audio_path:
            av_player.play_file(self._audio_path)

    def _clear_audio(self) -> None:
        self._audio_path = ""
        self.audio_label.setText(tr.weibao_no_audio())
        self._invalidate("capture")

    def _preview_capture(self) -> None:
        if (
            self.capture_model.currentData() is None
            or self.capture_deck.currentData() is None
        ):
            return
        draft = CaptureDraft(
            self.capture_model.currentData(),
            self.capture_deck.currentData(),
            tuple(
                (field, edit.toPlainText())
                for field, edit in self._capture_fields.items()
            ),
            tuple(self.capture_tags.text().split()),
            self.source_field.currentData() or "",
            self.source_url.text().strip(),
            self.source_title.text(),
            self.audio_field.currentData() or "",
            self._audio_path,
        )

        def preview(
            col: Collection,
        ) -> tuple[CaptureDraft, tuple[tuple[str, str], ...]]:
            note = capture_note(col, draft)
            digest = (
                hashlib.sha256(read_audio(draft.audio_path)).hexdigest()
                if draft.audio_path
                else ""
            )
            return replace(draft, audio_digest=digest), tuple(note.items())

        def ready(data: tuple[CaptureDraft, tuple[tuple[str, str], ...]]) -> None:
            self._draft, fields = data
            rendered = "".join(
                f"<h3>{html.escape(field)}</h3><p>{value}</p>"
                for field, value in fields
            )
            if draft.audio_path:
                rendered += (
                    "<p>"
                    + html.escape(
                        tr.weibao_audio_preview(
                            name=Path(draft.audio_path).name, field=draft.audio_field
                        )
                    )
                    + "</p>"
                )
            self.capture_preview.setHtml(rendered)
            self.capture_accept.setEnabled(True)

        self._invalidate("capture")
        self._query(preview, ready, "capture")

    def _accept_capture(self) -> None:
        if draft := self._draft:
            self._mutate(lambda col: add_capture(col, draft), "capture")

    def _break_tab(self) -> None:
        layout = self._tab(tr.weibao_break(), tr.weibao_break_help())
        form = QFormLayout()
        self.break_search = QLineEdit()
        form.addRow(tr.weibao_search(), self.break_search)
        qconnect(self.break_search.textChanged, lambda: self._invalidate("break"))
        self.break_start = QSpinBox()
        self.break_start.setRange(0, 60)
        self.break_days = QSpinBox()
        self.break_days.setRange(1, 30)
        self.break_days.setValue(3)
        self.break_spread = QSpinBox()
        self.break_spread.setRange(1, 60)
        self.break_spread.setValue(7)
        for label, spin in (
            (tr.weibao_start(), self.break_start),
            (tr.weibao_break_days(), self.break_days),
            (tr.weibao_return_days(), self.break_spread),
        ):
            form.addRow(label, spin)
            qconnect(spin.valueChanged, lambda: self._invalidate("break"))
        layout.addLayout(form)
        self.break_table = table(
            [tr.weibao_day(), tr.weibao_before(), tr.weibao_after()]
        )
        layout.addWidget(self.break_table)
        self.break_summary = QLabel()
        layout.addWidget(self.break_summary)
        actions = QHBoxLayout()
        self._button(actions, tr.weibao_preview(), self._preview_break)
        self.break_accept = self._button(
            actions, tr.weibao_apply_break(), self._accept_break
        )
        self.break_accept.setEnabled(False)
        layout.addLayout(actions)

    def _preview_break(self) -> None:
        search, start, days, spread = (
            self.break_search.text(),
            self.break_start.value(),
            self.break_days.value(),
            self.break_spread.value(),
        )
        self._invalidate("break")
        self._query(
            lambda col: plan_break(col, search, start, days, spread),
            self._show_break,
            "break",
        )

    def _show_break(self, plan: BreakPlan) -> None:
        self._plan = plan
        self.break_table.setRowCount(len(plan.before))
        for row, (before, after) in enumerate(
            zip(plan.before, plan.after, strict=True)
        ):
            for column, value in enumerate((row, before, after)):
                self.break_table.setItem(row, column, NumberItem(value))
        self.break_table.resizeColumnsToContents()
        self.break_summary.setText(tr.weibao_break_preview(count=len(plan.moves)))
        self.break_accept.setEnabled(bool(plan.moves))

    def _accept_break(self) -> None:
        if plan := self._plan:
            self._mutate(lambda col: apply_break(col, plan), "break")

    def _retention_tab(self) -> None:
        layout = self._tab(tr.weibao_retention(), tr.weibao_retention_help())
        form = QFormLayout()
        self.retention_deck = QComboBox()
        self.retention_values = QLineEdit("0.80, 0.90, 0.95")
        self.retention_days = QSpinBox()
        self.retention_days.setRange(30, 365)
        self.retention_days.setValue(90)
        for label, widget in (
            (tr.weibao_deck(), self.retention_deck),
            (tr.weibao_retention_values(), self.retention_values),
            (tr.weibao_horizon(), self.retention_days),
        ):
            form.addRow(label, widget)
        layout.addLayout(form)
        qconnect(self.retention_deck.currentIndexChanged, self._retention_changed)
        qconnect(self.retention_values.textChanged, self._retention_changed)
        qconnect(self.retention_days.valueChanged, self._retention_changed)
        self.retention_table = table(
            [
                tr.weibao_retention_target(),
                tr.weibao_review_average(),
                tr.weibao_minutes(),
                tr.weibao_memorized(),
            ]
        )
        layout.addWidget(self.retention_table)
        self._button(layout, tr.weibao_compare(), self._compare_retention)
        self._button(layout, tr.weibao_open_options(), self._deck_options)

    def _retention_changed(self) -> None:
        self._invalidate("retention")
        self.retention_table.setRowCount(0)

    def _compare_retention(self) -> None:
        did = self.retention_deck.currentData()
        if did is None:
            return
        try:
            retentions = tuple(
                float(value.strip())
                for value in self.retention_values.text().split(",")
            )
        except ValueError:
            showWarning(
                "Enter comma-separated retention values, such as 0.80, 0.90, 0.95.",
                parent=self,
            )
            return
        days = self.retention_days.value()
        self._query(
            lambda col: compare_retention(col, did, retentions, days),
            self._show_retention,
            "retention",
        )

    def _show_retention(self, results: list[RetentionResult]) -> None:
        self.retention_table.setRowCount(len(results))
        for row, result in enumerate(results):
            for column, value in enumerate(
                (result.retention, result.reviews, result.minutes, result.memorized)
            ):
                self.retention_table.setItem(
                    row, column, NumberItem(value, decimals=2 if column == 0 else 1)
                )
        self.retention_table.resizeColumnsToContents()

    def _deck_options(self) -> None:
        if did := self.retention_deck.currentData():
            from anki.decks import DeckId

            display_options_for_deck_id(DeckId(did))

    def _finish(self, _result: int) -> None:
        self._closed = True
        gui_hooks.operation_did_execute.remove(self._operation_did_execute)
        self.mw.pm.profile["weibao_study_columns"] = (
            self.overview.horizontalHeader().saveState().toHex().data().decode()
        )


def install(mw: AnkiQt) -> None:
    dialog: StudyDialog | None = None

    def show() -> None:
        nonlocal dialog
        if mw.col is None:
            return
        if dialog is None:
            dialog = StudyDialog(mw)
            qconnect(dialog.finished, closed)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def closed(_result: int) -> None:
        nonlocal dialog
        dialog = None

    def close_profile() -> None:
        if dialog:
            dialog.close()

    action = mw.form.menuTools.addAction(tr.weibao_study_tools())
    qconnect(action.triggered, show)
    gui_hooks.profile_will_close.append(close_profile)

    def home_entry(_browser: DeckBrowser, content: DeckBrowserContent) -> None:
        label = html.escape(tr.weibao_study_tools())
        content.stats += f"<p><button type='button' onclick=\"pycmd('weibao:study-tools')\">{label}</button></p>"

    def bridge(
        handled: tuple[bool, Any], message: str, context: Any
    ) -> tuple[bool, Any]:
        if (
            not handled[0]
            and message == "weibao:study-tools"
            and isinstance(context, DeckBrowser)
        ):
            show()
            return True, None
        return handled

    gui_hooks.deck_browser_will_render_content.append(home_entry)
    gui_hooks.webview_did_receive_js_message.append(bridge)
