# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Launch a synthetic profile, never the default base or installed app."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from aqt.profiles import ProfileManager

base = Path(tempfile.mkdtemp(prefix="anki-study-runtime-"))
pm = ProfileManager(base)
pm.setupMeta()
pm.meta.update(
    firstRun=False, updates=False, defaultLang="en_US", check_for_addon_updates=False
)
pm.setLang("en_US")
for name in ("StudyRuntime", "SecondRuntime"):
    pm.create(name)
    pm.load(name)
    pm.profile.update(autoSync=False, syncMedia=False)
    pm.save()
pm.db.close()
addon = base / "addons21" / "study_runtime"
addon.mkdir(parents=True)
shutil.copyfile(Path(__file__).with_name("probe.py"), addon / "__init__.py")
if helper_source := os.environ.get("STUDY_RUNTIME_HELPER_SOURCE"):
    shutil.copytree(
        helper_source,
        base / "addons21" / "759844606",
        ignore=shutil.ignore_patterns(".git", "__pycache__"),
    )
env = dict(os.environ)
env.update(
    ANKI_SINGLE_INSTANCE_KEY=base.name,
    ANKI_API_PORT="40019",
    ANKICONNECT_BIND_PORT="8779",
    QTWEBENGINE_REMOTE_DEBUGGING="",
    STUDY_RUNTIME_BASE=str(base),
)
print(f"Synthetic runtime evidence: {base}", flush=True)
with (base / "application.log").open("w") as log:
    result = subprocess.run(
        ["just", "run", "-b", str(base), "-p", "StudyRuntime"],
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        timeout=180,
    )
report = base / "report.txt"
print(report.read_text() if report.exists() else (base / "application.log").read_text())
if result.returncode or not report.exists() or "PASS all" not in report.read_text():
    raise SystemExit(1)

# Test-only startup hook observes safe mode even though Anki skips add-ons.
bootstrap = base / "safe-bootstrap"
bootstrap.mkdir()
shutil.copyfile(
    Path(__file__).with_name("safe_probe.py"), bootstrap / "sitecustomize.py"
)
env["PYTHONPATH"] = str(bootstrap) + os.pathsep + env.get("PYTHONPATH", "")
with (base / "safe-application.log").open("w") as log:
    safe = subprocess.run(
        ["just", "run", "-b", str(base), "-p", "SecondRuntime", "--safemode"],
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        timeout=60,
    )
print(report.read_text())
if safe.returncode or "PASS safe mode" not in report.read_text():
    print((base / "safe-application.log").read_text())
    raise SystemExit(1)
