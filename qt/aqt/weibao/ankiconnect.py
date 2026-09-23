# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Start the bundled AnkiConnect API when no add-on owns it."""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aqt.main import AnkiQt

_server: object | None = None
ADDON_ID = "2055492159"


def install(mw: AnkiQt) -> bool:
    """Hook profile lifecycle and respect an installed add-on's own settings."""
    from aqt import gui_hooks

    if ADDON_ID in mw.addonManager.allAddons():
        return False
    gui_hooks.profile_did_open.append(lambda: _start(mw))
    gui_hooks.profile_will_close.append(_stop)
    return True


def _start(mw: AnkiQt) -> None:
    """Bind only while a collection profile is open."""
    global _server
    try:
        from .ankiconnect_vendor import AnkiConnect, Edit, util

        config_path = Path(mw.pm.profileFolder()) / "weibao_ankiconnect.json"
        if config_path.is_file():
            config = json.loads(config_path.read_text(encoding="utf-8"))
            if not isinstance(config, dict):
                raise ValueError(f"AnkiConnect config must be an object: {config_path}")
        else:
            config = {}
        util.configure_fork(config)
        Edit.register_with_anki()
        server = AnkiConnect()
        server.initLogging()
        if server.startWebServer():
            _server = server
        elif server.log is not None:
            server.log.close()
    except Exception:
        traceback.print_exc()


def _stop() -> None:
    global _server
    if _server is not None:
        from .ankiconnect_vendor import AnkiConnect

        server = _server
        assert isinstance(server, AnkiConnect)
        if server.timer is not None:
            server.timer.stop()
        server.server.close()
        if server.log is not None:
            server.log.close()
        _server = None
