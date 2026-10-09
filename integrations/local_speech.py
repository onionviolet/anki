# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Local WAV speech with a Mandarin voice for Han text, or an explicit language."""

import argparse
import platform
import re
import subprocess
from pathlib import Path

from anki.mac_speech import MacSpeechVoice, parse_voice_line, voice_preference


def select_voice(lang: str, requested: str) -> MacSpeechVoice:
    result = subprocess.run(
        ["/usr/bin/say", "-v", "?"],
        capture_output=True,
        check=True,
        encoding="utf8",
        timeout=10,
    )
    voices = [
        voice
        for line in result.stdout.splitlines()
        if (voice := parse_voice_line(line))
    ]
    if lang:
        voices = [voice for voice in voices if voice.lang == lang]
    if requested:
        voices = [voice for voice in voices if voice.name == requested]
    if not voices:
        raise ValueError(
            f"No installed voice matches language {lang!r} and voice {requested!r}."
        )
    return min(voices, key=lambda voice: voice_preference(voice.name, voice.lang))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text")
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--lang", default="auto", help="auto, system, or a code such as zh_CN/zh_TW"
    )
    parser.add_argument("--voice", default="", help="Exact installed macOS voice name")
    parser.add_argument(
        "--rate", type=int, default=170, help="Speech rate in words per minute"
    )
    args = parser.parse_args()
    if platform.system() != "Darwin" or not Path("/usr/bin/say").is_file():
        parser.error("This adapter requires macOS system speech.")
    if not args.text.strip() or len(args.text) > 10000:
        parser.error("Provide 1 to 10,000 characters of text.")
    if args.output.suffix.lower() != ".wav" or args.output.exists():
        parser.error("Choose a new .wav output path.")
    if not 50 <= args.rate <= 400:
        parser.error("Choose a speech rate between 50 and 400 words per minute.")
    lang = args.lang.replace("-", "_")
    if lang == "auto":
        # Han text is assumed to be Mandarin. Kana identifies Japanese text;
        # use an explicit language for other languages written with Hanzi.
        han = re.search(r"[\u3400-\u4dbf\u4e00-\u9fff]", args.text)
        kana = re.search(r"[\u3040-\u30ff]", args.text)
        # An explicitly selected voice overrides the automatic language guess.
        lang = "zh_CN" if han and not kana and not args.voice else ""
    elif lang == "system":
        lang = ""
    voice_args = []
    if lang or args.voice:
        try:
            voice = select_voice(lang, args.voice)
        except ValueError as error:
            parser.error(str(error))
        voice_args = ["-v", voice.name]
        print(f"Voice: {voice.name} ({voice.lang}), rate: {args.rate}")
    subprocess.run(
        [
            "/usr/bin/say",
            *voice_args,
            "-r",
            str(args.rate),
            "--data-format=LEI16@22050",
            "-o",
            str(args.output),
            "--",
            args.text,
        ],
        check=True,
        timeout=60,
    )
    print(args.output.resolve())


if __name__ == "__main__":
    main()
