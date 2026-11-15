"""Reproduce the macOS Browse accessibility crash in a disposable Anki base.

Run with the Python of the environment under test, for example:

    "$HOME/Library/Application Support/AnkiWeibao/venv/bin/python" run.py 15

It creates a temporary base with 30 synthetic Basic notes, opens Browse
through the bundled AnkiConnect server, repeats searches and screen changes,
and walks the window's accessibility tree with ./axwalk (build it with
`swiftc -O axwalk.swift -o axwalk`; the terminal needs Accessibility access).
It never opens the default base. Prints crashed=True/False.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from aqt.profiles import ProfileManager

HERE = Path(__file__).resolve().parent
seconds = sys.argv[1] if len(sys.argv) > 1 else "15"
api_port = "8781"

base = Path(tempfile.mkdtemp(prefix="anki-ax-repro-"))
pm = ProfileManager(base)
pm.setupMeta()
pm.meta.update(
    firstRun=False,
    updates=False,
    check_for_updates=False,
    defaultLang="en_US",
    check_for_addon_updates=False,
)
pm.setLang("en_US")
pm.create("AX")
pm.load("AX")
pm.profile.update(autoSync=False, syncMedia=False)
pm.save()
pm.db.close()

env = dict(
    os.environ,
    ANKI_SINGLE_INSTANCE_KEY=base.name,
    ANKI_API_PORT="40021",
    ANKICONNECT_BIND_PORT=api_port,
)
log = open(base / "app.log", "w")
anki = subprocess.Popen(
    [sys.executable, "-c", "import aqt; aqt.run()", "-b", str(base), "-p", "AX"],
    env=env,
    stdout=log,
    stderr=subprocess.STDOUT,
)


def ac(action: str, **params: object) -> object:
    req = urllib.request.Request(
        f"http://127.0.0.1:{api_port}",
        json.dumps({"action": action, "version": 6, "params": params}).encode(),
    )
    return json.load(urllib.request.urlopen(req, timeout=10))


for _ in range(60):
    try:
        ac("version")
        break
    except Exception:
        time.sleep(1)

ac(
    "addNotes",
    notes=[
        {
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": f"q{i}", "Back": f"a{i}"},
        }
        for i in range(30)
    ],
)
walker = subprocess.Popen([str(HERE / "axwalk"), str(anki.pid), seconds])
cycles = 0
while walker.poll() is None and anki.poll() is None:
    try:
        ac("guiBrowse", query="deck:Default")
        ac("guiBrowse", query="q1*")
        time.sleep(1)
        ac("guiDeckBrowser")
        ac("guiBrowse", query="deck:Default")
        cycles += 1
    except Exception:
        pass
walker.wait()
crashed = anki.poll() is not None
print(f"ui_cycles={cycles} anki_exit={anki.poll()} crashed={crashed} base={base}")
if not crashed:
    anki.terminate()
    anki.wait(15)
