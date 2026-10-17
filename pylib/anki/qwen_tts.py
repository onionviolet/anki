# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Optional local Qwen runtime configuration, without importing MLX into Anki."""

from __future__ import annotations

import hashlib
import json
import math
import os
import selectors
import subprocess
import threading
import time
import wave
from dataclasses import dataclass
from pathlib import Path

MODEL_ID = "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-4bit"
MODEL_REVISION = "f35faf19b0cc2160865af64ecf0f22f83d335135"
MLX_AUDIO_VERSION = "0.5.7"
SPEAKERS = ("Vivian", "Serena", "Uncle_Fu")
INSTRUCTION = "请用清晰自然的标准普通话朗读。"


def runtime_root() -> Path:
    return Path(
        os.environ.get(
            "ANKI_QWEN_TTS_ROOT",
            str(Path.home() / "Library/Application Support/AnkiQwenTTS"),
        )
    )


@dataclass(frozen=True)
class QwenRuntime:
    python: Path
    model: Path
    revision: str
    cache: Path

    @classmethod
    def read(cls, root: Path | None = None) -> QwenRuntime | None:
        root = root or runtime_root()
        config_path = root / "config.json"
        if not config_path.is_file():
            return None
        data = json.loads(config_path.read_text(encoding="utf8"))
        if data.get("schema") != 1 or data.get("mlx_audio") != MLX_AUDIO_VERSION:
            raise ValueError(
                "Qwen runtime configuration is incompatible. Run qwen-setup again."
            )
        runtime = cls(
            Path(data["python"]), Path(data["model"]), data["revision"], root / "audio"
        )
        if (
            not runtime.python.is_file()
            or not (runtime.model / "config.json").is_file()
        ):
            raise ValueError("Qwen runtime or model is missing. Run qwen-setup again.")
        return runtime

    def audio_path(self, text: str, speaker: str, speed: float) -> Path:
        validate_request(text, speaker, speed)
        request = {
            "schema": 1,
            "model": str(self.model),
            "revision": self.revision,
            "engine": MLX_AUDIO_VERSION,
            "text": text,
            "speaker": speaker,
            "speed": speed,
            "instruction": INSTRUCTION,
        }
        digest = hashlib.sha256(
            json.dumps(request, sort_keys=True, ensure_ascii=False).encode("utf8")
        ).hexdigest()
        return self.cache / f"qwen-{digest}.wav"


def validate_request(text: str, speaker: str, speed: float) -> None:
    if not text.strip() or len(text) > 2000:
        raise ValueError("Qwen speech needs 1 to 2,000 characters of text.")
    if speaker not in SPEAKERS:
        raise ValueError(f"Choose a Qwen speaker from {', '.join(SPEAKERS)}.")
    if not math.isfinite(speed) or not 0.5 <= speed <= 2:
        raise ValueError("Qwen speech speed must be between 0.5 and 2.")


def valid_audio(path: Path) -> bool:
    try:
        with wave.open(str(path)) as audio:
            return (
                audio.getnchannels() == 1
                and audio.getsampwidth() == 2
                and audio.getframerate() == 24000
                and audio.getnframes() > 0
                and len(audio.readframes(audio.getnframes())) == audio.getnframes() * 2
            )
    except (OSError, EOFError, wave.Error):
        return False


class QwenCancelled(Exception):
    pass


class QwenWorker:
    """Serialize generation in a warm external process; Anki never imports MLX."""

    def __init__(self, runtime: QwenRuntime) -> None:
        self.runtime = runtime
        self._process: subprocess.Popen[bytes] | None = None
        self._lock = threading.Lock()

    def generate(
        self,
        text: str,
        speaker: str = "Vivian",
        speed: float = 1.0,
        cancelled: threading.Event | None = None,
        timeout: float = 300,
    ) -> Path:
        cancelled = cancelled or threading.Event()
        path = self.runtime.audio_path(text, speaker, speed)
        with self._lock:
            if cancelled.is_set():
                raise QwenCancelled()
            if valid_audio(path):
                return path
            process = self._start()
            assert process.stdin is not None and process.stdout is not None
            request = {
                "text": text,
                "speaker": speaker,
                "speed": speed,
                "instruction": INSTRUCTION,
                "output": str(path),
            }
            try:
                process.stdin.write(
                    (json.dumps(request, ensure_ascii=False) + "\n").encode("utf8")
                )
                process.stdin.flush()
                response = self._response(process, cancelled, timeout)
                if error := response.get("error"):
                    raise RuntimeError(str(error))
                if response.get("path") != str(path) or not valid_audio(path):
                    raise RuntimeError("Qwen returned invalid audio.")
                return path
            except Exception:
                self.close()
                raise

    def _start(self) -> subprocess.Popen[bytes]:
        if self._process is None or self._process.poll() is not None:
            self.close()
            self.runtime.cache.mkdir(parents=True, exist_ok=True)
            env = dict(os.environ)
            env.pop("PYTHONPATH", None)
            env.update(
                HF_HUB_OFFLINE="1",
                TRANSFORMERS_OFFLINE="1",
                PYTHONNOUSERSITE="1",
                TOKENIZERS_PARALLELISM="false",
            )
            with (self.runtime.cache.parent / "worker.log").open("w") as log:
                self._process = subprocess.Popen(
                    [
                        str(self.runtime.python),
                        "-I",
                        "-u",
                        "-c",
                        "import runpy,sys; path=sys.argv.pop(1); runpy.run_path(path,run_name='__main__')",
                        str(Path(__file__).with_name("_qwen_tts_worker.py")),
                        str(self.runtime.model),
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=log,
                    env=env,
                )
        return self._process

    def _response(
        self,
        process: subprocess.Popen[bytes],
        cancelled: threading.Event,
        timeout: float,
    ) -> dict:
        assert process.stdout is not None
        deadline = time.monotonic() + timeout
        buffer = b""
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while b"\n" not in buffer:
                if cancelled.is_set():
                    raise QwenCancelled()
                if time.monotonic() >= deadline:
                    raise TimeoutError("Local Qwen speech timed out.")
                if selector.select(0.1):
                    chunk = os.read(process.stdout.fileno(), 4096)
                    if not chunk:
                        raise RuntimeError(
                            "Qwen worker stopped. See the runtime's worker.log."
                        )
                    buffer += chunk
                    if len(buffer) > 65536:
                        raise RuntimeError("Qwen returned an oversized response.")
        response = json.loads(buffer.split(b"\n", 1)[0])
        if not isinstance(response, dict):
            raise RuntimeError("Qwen returned an invalid response.")
        return response

    def abort(self) -> None:
        if self._process is not None and self._process.poll() is None:
            try:
                self._process.terminate()
            except ProcessLookupError:
                pass

    def close(self) -> None:
        process, self._process = self._process, None
        if process is None:
            return
        if process.stdin:
            try:
                process.stdin.close()
            except OSError:
                pass
        if process.poll() is None:
            try:
                process.wait(timeout=1)
            except ProcessLookupError:
                pass
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1)
        if process.stdout:
            process.stdout.close()
