# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Make the pinned Chinese Support 3 add-on available to this Anki base."""

import shutil
import tempfile
from pathlib import Path

ADDON_ID = "1752008591"


def bundled_source() -> Path:
    packaged = Path(__file__).resolve().parent / "chinese_support_vendor"
    if (packaged / "__init__.py").is_file():
        return packaged
    source = (
        Path(__file__).resolve().parents[3]
        / "integrations"
        / "chinese-support-3"
        / "chinese"
    )
    if (source / "__init__.py").is_file():
        return source
    raise FileNotFoundError("Chinese Support 3 submodule is not initialized")


def install(addons_folder: str) -> bool:
    """Copy once, preserving any existing user-installed version and config."""
    folder = Path(addons_folder)
    destination = folder / ADDON_ID
    if destination.exists() or destination.is_symlink():
        return False
    with tempfile.TemporaryDirectory(prefix="chinese-support3-", dir=folder) as tmp:
        staged = Path(tmp) / ADDON_ID
        shutil.copytree(bundled_source(), staged)
        staged.rename(destination)
    return True
