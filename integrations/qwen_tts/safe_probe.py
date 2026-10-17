# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Test-only bootstrap observes audio registration in safe mode."""

import os
from pathlib import Path

from aqt import gui_hooks
from aqt.qt import QTimer


def check():
    import aqt
    from aqt.sound import av_player
    from aqt.weibao.qwen_tts import QwenTTSPlayer

    assert aqt.mw.safeMode
    assert not any(isinstance(p, QwenTTSPlayer) for p in av_player.players)
    with (Path(os.environ["QWEN_RUNTIME_BASE"]) / "report.txt").open("a") as file:
        file.write("PASS safe mode\n")
    aqt.mw.unloadProfileAndExit()


gui_hooks.profile_did_open.append(lambda: QTimer.singleShot(500, check))
