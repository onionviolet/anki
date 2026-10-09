# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Test-only startup observer; production safe mode still skips all add-ons."""

import os
import sys
import traceback
from pathlib import Path

import aqt
from aqt import gui_hooks
from aqt.qt import QTimer


def check():
    report = Path(os.environ["STUDY_RUNTIME_BASE"]) / "report.txt"
    try:
        mw = aqt.mw
        assert mw.safeMode
        assert not any(a.text() == "Study tools" for a in mw.form.menuTools.actions())
        assert "aqt.weibao.ankiconnect_vendor" not in sys.modules
        assert "study_runtime" not in sys.modules
        assert not any(
            "study_dialog" in hook.__module__
            for hook in gui_hooks.deck_browser_will_render_content._hooks
        )
        with report.open("a") as file:
            file.write(
                "PASS safe mode: no Study tools menu/home hook, bundled API or test add-on loaded\n"
            )
        mw.unloadProfileAndExit()
    except Exception:
        with report.open("a") as file:
            file.write(traceback.format_exc())
        aqt.mw.unloadProfileAndExit()


gui_hooks.profile_did_open.append(lambda: QTimer.singleShot(1000, check))
