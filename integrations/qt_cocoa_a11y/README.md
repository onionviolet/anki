# Qt Cocoa accessibility patch (Browse crash)

_Type: CURRENT-STATE. Audience: maintainer reference._

## Problem

On macOS, Anki segfaults when an accessibility client reads the Browse window
while the card table has rows and a selection. On this Mac the client was Codex
Computer Use (`SkyComputerUseService`, for Computer History). Raycast,
VoiceOver, window tilers and screen-sharing tools use the same API.

The crash is in Qt's Cocoa platform plugin (`libqcocoa.dylib`), not Anki. Qt
creates placeholder row and cell elements that reuse the table's accessibility
ID. When a real selected cell replaces a placeholder, the placeholder's
`dealloc` and `removeElementsFromCache` call `deleteInterface(axid)` with the
table's ID. That destroys the live table interface while macOS still holds it.

- Upstream: QTBUG-149612, regression from Qt commit `b1ed5f65`, proposed fix
  in Qt Gerrit change 765434. As of 2026-11-14, no released Qt or PyQt wheel
  contains the fix.
- Public report: <https://forums.ankiweb.net/t/macos-accessibility-scan-can-crash-browse-when-a-row-is-selected/70882>
- Reproduced here on Qt 6.9.1, 6.10.2 and 6.11.2 with the fork's code and
  with upstream Anki's table code. An empty table never crashed. These had no
  effect: `--disable-renderer-accessibility`, `QT_ACCESSIBILITY=0`, the fork's
  sidebar and editor.

## Patch

[`qcocoa-table-axid-ownership.patch`](qcocoa-table-axid-ownership.patch)
applies to qtbase `v6.11.2`. It adds two guards: parent-managed (synthesized)
elements never delete an interface by ID. Real cells still clean up their own
IDs. This was written from the regression description because Gerrit's patch
download was unreachable; compare it with change 765434 when that merges.

## Rebuild and install

`build-and-install.sh` clones qtbase `v6.11.2`, applies the patch, builds only
`QCocoaIntegrationPlugin`, backs up the installed plugin under
`~/Library/Application Support/AnkiWeibao/rollbacks/`, and installs the patched
plugin. Rerun it after any change to the installed `pyqt6-qt6` version. The
plugin uses Qt private API, so it must be built from the same Qt version as the
installed wheel.

Rollback: copy `libqcocoa.dylib` from the dated rollback folder back to
`venv/lib/python3.13/site-packages/PyQt6/Qt6/plugins/platforms/`.

Remove this patch once a `pyqt6-qt6` release includes the Qt fix.

## Repro

`repro/run.py` launches a disposable base, adds 30 synthetic notes, opens
Browse through AnkiConnect, and walks the accessibility tree with
`repro/axwalk`. Run it with the Python of the environment under test. It
prints `crashed=True` or `crashed=False`. `repro/probe_addon.py` is the
component-bisect probe used during diagnosis and is not needed for the repro.
