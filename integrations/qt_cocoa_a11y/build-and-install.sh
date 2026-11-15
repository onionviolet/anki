#!/bin/bash
# Build Qt's Cocoa platform plugin with the table accessibility ownership fix
# and install it into the Anki Weibao venv, keeping a rollback copy.
# Usage: build-and-install.sh [work_dir]   (default ~/code/qt-cocoa-patch)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:-$HOME/code/qt-cocoa-patch}"
VENV="$HOME/Library/Application Support/AnkiWeibao/venv"
PY="$VENV/bin/python"
QT_VERSION="$("$PY" -c 'import importlib.metadata as m; print(m.version("pyqt6-qt6"))')"
PLUGIN_DIR="$VENV/lib/python3.13/site-packages/PyQt6/Qt6/plugins/platforms"

echo "Installed pyqt6-qt6: $QT_VERSION"
mkdir -p "$WORK"
if [ ! -d "$WORK/qtbase" ]; then
    git clone --depth 1 -b "v$QT_VERSION" https://code.qt.io/qt/qtbase.git "$WORK/qtbase"
fi
cd "$WORK/qtbase"
if git apply --check "$HERE/qcocoa-table-axid-ownership.patch" 2>/dev/null; then
    git apply "$HERE/qcocoa-table-axid-ownership.patch"
elif ! git apply --reverse --check "$HERE/qcocoa-table-axid-ownership.patch" 2>/dev/null; then
    echo "Patch does not apply to qtbase v$QT_VERSION" >&2
    exit 1
fi

mkdir -p "$WORK/build"
cd "$WORK/build"
if [ ! -f build.ninja ]; then
    ../qtbase/configure -release -nomake tests -nomake examples \
        -prefix "$WORK/install" -- -G Ninja -DQT_NO_APPLE_SDK_MAX_VERSION_CHECK=ON
fi
ninja QCocoaIntegrationPlugin
BUILT="$WORK/build/plugins/platforms/libqcocoa.dylib"

# Match the wheel's rpath so the plugin loads the venv's Qt frameworks.
for rp in $(otool -l "$BUILT" | awk '/LC_RPATH/{getline; getline; print $2}'); do
    install_name_tool -delete_rpath "$rp" "$BUILT"
done
install_name_tool -add_rpath "@loader_path/../../lib" "$BUILT"
codesign --force --sign - "$BUILT"

ROLLBACK="$VENV/../rollbacks/$(date +%F)-qcocoa-before-a11y-patch"
mkdir -p "$ROLLBACK"
[ -f "$ROLLBACK/libqcocoa.dylib" ] || cp -p "$PLUGIN_DIR/libqcocoa.dylib" "$ROLLBACK/"
cp "$BUILT" "$PLUGIN_DIR/libqcocoa.dylib"
shasum -a 256 "$ROLLBACK/libqcocoa.dylib" "$PLUGIN_DIR/libqcocoa.dylib"
echo "Installed patched plugin. Rollback copy: $ROLLBACK"
