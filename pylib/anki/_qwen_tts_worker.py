# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Standalone optional worker. Its MLX dependencies live outside Anki's env."""

import contextlib
import importlib
import json
import os
import sys
import tempfile
import traceback
import wave
from pathlib import Path


def main() -> None:
    protocol = sys.stdout
    model = None
    for line in sys.stdin:
        try:
            request = json.loads(line)
            with contextlib.redirect_stdout(sys.stderr):
                # These modules deliberately live only in the external runtime.
                mx = importlib.import_module("mlx.core")
                np = importlib.import_module("numpy")
                load_model = importlib.import_module("mlx_audio.tts.utils").load_model

                if model is None:
                    print(
                        "Loading local Qwen Mandarin model.",
                        file=sys.stderr,
                        flush=True,
                    )
                    model = load_model(sys.argv[1])
                mx.random.seed(0)
                segments = list(
                    model.generate_custom_voice(
                        text=request["text"],
                        speaker=request["speaker"],
                        language="Chinese",
                        instruct=request["instruction"],
                        temperature=0.7,
                        max_tokens=4096,
                        verbose=False,
                    )
                )
                if not segments or any(part.sample_rate != 24000 for part in segments):
                    raise ValueError("Qwen produced no usable 24 kHz audio.")
                audio = np.concatenate(
                    [np.asarray(part.audio) for part in segments]
                ).reshape(-1)
                if request["speed"] != 1:
                    librosa = importlib.import_module("librosa")

                    audio = librosa.effects.time_stretch(audio, rate=request["speed"])
                if not audio.size or not np.isfinite(audio).all():
                    raise ValueError("Qwen produced empty or nonfinite audio.")
                pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()
                path = Path(request["output"])
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(
                        dir=path.parent, suffix=".wav", delete=False
                    ) as file:
                        temporary = Path(file.name)
                    with wave.open(str(temporary), "wb") as output:
                        output.setnchannels(1)
                        output.setsampwidth(2)
                        output.setframerate(24000)
                        output.writeframes(pcm)
                    os.replace(temporary, path)
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
                response = {"path": str(path)}
        except Exception as error:
            traceback.print_exc(file=sys.stderr)
            response = {"error": f"{type(error).__name__}: {error}"[:1000]}
        protocol.write(json.dumps(response, ensure_ascii=False) + "\n")
        protocol.flush()


if __name__ == "__main__":
    main()
