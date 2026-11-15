import os
mode = os.environ.get("AXPROBE", "")
if "nosidebar" in mode:
    from aqt.browser.sidebar import tree
    tree.SidebarTreeView.refresh = lambda self, new_current=None: None
if "noeditor" in mode:
    from aqt.browser import browser
    browser.Browser.on_all_or_selected_rows_changed = lambda self: None
    browser.Browser.on_current_row_changed = lambda self: None
if "noaccess" in mode:
    from aqt.qt import QAccessible
    # Try to keep Qt from creating accessible interfaces for widgets.
    QAccessible.installFactory(lambda key, obj: None)
from aqt import gui_hooks
def _hide(b):
    if "hidetable" in mode: b.table._view.hide()
    if "hidesidebar" in mode: b.sidebarDockWidget.hide()
    if "hideeditor" in mode: b.editor.web.hide()
    if "hidesearch" in mode: b.form.searchEdit.hide()
    if "hidetoolbar" in mode:
        for w in (b.form.toolbar if hasattr(b.form, "toolbar") else []): pass
gui_hooks.browser_will_show.append(_hide)
if "plaintable" in mode:
    from aqt.qt import QAccessible, QAccessibleWidget, QTableView
    _keep = []
    def _factory(key, obj):
        if isinstance(obj, QTableView):
            iface = QAccessibleWidget(obj, QAccessible.Role.Table)
            _keep.append(iface)
            return iface
        return None
    QAccessible.installFactory(_factory)
def _tweak(b):
    v = b.table._view
    if "nohh" in mode: v.horizontalHeader().hide()
    if "novh" in mode: v.verticalHeader().hide()
    if "sharedsel" in mode: v.horizontalHeader().setSelectionModel(v.selectionModel())
    if "nodelegate" in mode:
        from aqt.qt import QStyledItemDelegate
        v.setItemDelegate(QStyledItemDelegate(v))
    if "emptymodel" in mode:
        b.table._model.search = lambda ctx: None
gui_hooks.browser_will_show.append(_tweak)
def _nofocus(b):
    if "nofocus" in mode:
        from aqt.qt import Qt
        b.table._view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
gui_hooks.browser_will_show.append(_nofocus)
