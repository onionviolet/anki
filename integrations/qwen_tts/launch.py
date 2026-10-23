# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Exercise real reviewer speech in a synthetic, offscreen Anki profile."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from anki.qwen_tts import runtime_root
from aqt.profiles import ProfileManager


def main() -> None:
    base = Path(tempfile.mkdtemp(prefix="anki-qwen-runtime-"))
    runtime = base / "qwen"
    runtime.mkdir()
    shutil.copyfile(runtime_root() / "config.json", runtime / "config.json")
    pm = ProfileManager(base)
    pm.setupMeta()
    pm.meta.update(
        firstRun=False,
        updates=False,
        defaultLang="en_US",
        check_for_addon_updates=False,
    )
    pm.setLang("en_US")
    for name in ("QwenRuntime", "QwenSecond"):
        pm.create(name)
        pm.load(name)
        pm.profile.update(autoSync=False, syncMedia=False)
        pm.save()
    pm.db.close()
    addon = base / "addons21/qwen_runtime"
    addon.mkdir(parents=True)
    shutil.copyfile(Path(__file__).with_name("probe.py"), addon / "__init__.py")
    env = dict(os.environ)
    env.update(
        ANKI_QWEN_TTS_ROOT=str(runtime),
        QWEN_RUNTIME_BASE=str(base),
        ANKI_SINGLE_INSTANCE_KEY=base.name,
        ANKI_API_PORT="40021",
        ANKICONNECT_BIND_PORT="8781",
        QT_QPA_PLATFORM="offscreen",
        QTWEBENGINE_REMOTE_DEBUGGING="",
    )
    print(f"Qwen runtime evidence: {base}", flush=True)
    with (base / "application.log").open("w") as log:
        result = subprocess.run(
            ["just", "run", "-b", str(base), "-p", "QwenRuntime"],
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=240,
        )
    report = base / "report.txt"
    print(
        report.read_text()
        if report.exists()
        else (base / "application.log").read_text()
    )
    if result.returncode or not report.exists() or "PASS all" not in report.read_text():
        print((base / "application.log").read_text()[-6000:])
        raise SystemExit(1)
    bootstrap = base / "safe-bootstrap"
    bootstrap.mkdir()
    shutil.copyfile(
        Path(__file__).with_name("safe_probe.py"), bootstrap / "sitecustomize.py"
    )
    env["PYTHONPATH"] = str(bootstrap) + os.pathsep + env.get("PYTHONPATH", "")
    with (base / "safe.log").open("w") as log:
        safe = subprocess.run(
            ["just", "run", "-b", str(base), "-p", "QwenSecond", "--safemode"],
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=60,
        )
    if safe.returncode or "PASS safe mode" not in report.read_text():
        print((base / "safe.log").read_text()[-6000:])
        raise SystemExit(1)
    print("PASS safe mode")


if __name__ == "__main__":
    main()
