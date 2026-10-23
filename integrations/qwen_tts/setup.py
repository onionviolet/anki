# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Install the optional speech environment and a pinned local Mandarin model."""

import json
import platform
import subprocess
import sys
from pathlib import Path

from anki.qwen_tts import MLX_AUDIO_VERSION, MODEL_ID, MODEL_REVISION, runtime_root


def main() -> None:
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise SystemExit("Local Qwen speech requires an Apple Silicon Mac.")
    root = runtime_root()
    root.mkdir(parents=True, exist_ok=True)
    uv = Path("out/extracted/uv/uv").resolve()
    python = root / "venv/bin/python"
    if not python.is_file():
        subprocess.run(
            [str(uv), "venv", "--python", sys.executable, str(root / "venv")],
            check=True,
        )
    subprocess.run(
        [
            str(uv),
            "pip",
            "install",
            "--python",
            str(python),
            "-r",
            str(Path(__file__).with_name("requirements.txt")),
        ],
        check=True,
    )
    print(
        "Downloading the pinned Qwen model (about 2.3 GB), then checking the loader.",
        flush=True,
    )
    result = subprocess.run(
        [
            str(python),
            "-c",
            "import sys; from huggingface_hub import snapshot_download; "
            "path=snapshot_download(sys.argv[1],revision=sys.argv[2],allow_patterns=['*.json','*.txt','*.safetensors']); "
            "from mlx_audio.tts.utils import load_model; model=load_model(path); print(path)",
            MODEL_ID,
            MODEL_REVISION,
        ],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    model = Path(result.stdout.strip().splitlines()[-1])
    if not (model / "model.safetensors").is_file():
        raise SystemExit("Model verification failed; the runtime has not been enabled.")
    config = {
        "schema": 1,
        "python": str(python),
        "model": str(model),
        "model_id": MODEL_ID,
        "revision": MODEL_REVISION,
        "mlx_audio": MLX_AUDIO_VERSION,
    }
    temporary = root / "config.json.tmp"
    temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf8")
    temporary.replace(root / "config.json")
    freeze = subprocess.run(
        [str(uv), "pip", "freeze", "--python", str(python)],
        check=True,
        capture_output=True,
        text=True,
    )
    (root / "installed-requirements.txt").write_text(freeze.stdout, encoding="utf8")
    print(f"Qwen Mandarin speech is ready: {root}")


if __name__ == "__main__":
    main()
