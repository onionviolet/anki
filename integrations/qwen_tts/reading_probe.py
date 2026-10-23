# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Compare local reading profiles on synthetic text, without playing audio."""

import json
import tempfile
import wave
from dataclasses import replace
from pathlib import Path

import anki.qwen_tts as tts


def main() -> None:
    runtime = tts.QwenRuntime.read()
    assert runtime is not None
    base = Path(tempfile.mkdtemp(prefix="anki-qwen-reading-"))
    worker = tts.QwenWorker(replace(runtime, cache=base / "audio"))
    profiles = [
        ("original", "请用清晰自然的标准普通话朗读。", 0.7, 50, 1.0),
        ("simple", "清晰、平稳的标准普通话，语气中性。", 0.7, 50, 1.0),
        ("simple-conservative", "清晰、平稳的标准普通话，语气中性。", 0.45, 20, 0.9),
        ("no-instruction", "", 0.7, 50, 1.0),
    ]
    original_instruction = tts.INSTRUCTION
    original_settings = dict(tts.GENERATION_SETTINGS)
    results = []
    print(f"Reading profile evidence: {base}", flush=True)
    try:
        for name, instruction, temperature, top_k, top_p in profiles:
            tts.INSTRUCTION = instruction
            tts.GENERATION_SETTINGS.update(
                temperature=temperature, top_k=top_k, top_p=top_p
            )
            for text in ("使用。进步。我们每天学习中文。", "使用"):
                path = worker.generate(text)
                with wave.open(str(path)) as audio:
                    seconds = audio.getnframes() / audio.getframerate()
                item = dict(
                    profile=name,
                    text=text,
                    instruction=instruction,
                    settings=dict(tts.GENERATION_SETTINGS),
                    seconds=seconds,
                    audio=str(path),
                )
                results.append(item)
                (base / "report.json").write_text(
                    json.dumps(results, ensure_ascii=False, indent=2) + "\n"
                )
                print(f"{name}: {text!r}: {seconds:.2f}s", flush=True)
    finally:
        tts.INSTRUCTION = original_instruction
        tts.GENERATION_SETTINGS.update(original_settings)
        worker.close()


if __name__ == "__main__":
    main()
