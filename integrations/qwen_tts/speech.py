# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Generate a previewable WAV with the installed offline Qwen Mandarin model."""

import argparse
import shutil
from pathlib import Path

from anki.qwen_tts import SPEAKERS, QwenRuntime, QwenWorker


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text")
    parser.add_argument("output", type=Path)
    parser.add_argument("--speaker", choices=SPEAKERS, default="Vivian")
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()
    if args.output.exists() or args.output.suffix.lower() != ".wav":
        parser.error("Choose a new .wav output path.")
    runtime = QwenRuntime.read()
    if runtime is None:
        parser.error("Run just qwen-setup first.")
    worker = QwenWorker(runtime)
    try:
        audio = worker.generate(args.text, args.speaker, args.speed)
        with args.output.open("xb") as output, audio.open("rb") as source:
            shutil.copyfileobj(source, output)
    finally:
        worker.close()
    print(args.output.resolve())


if __name__ == "__main__":
    main()
