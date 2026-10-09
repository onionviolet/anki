# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Shared voice discovery and Mandarin preferences for macOS system speech."""

from __future__ import annotations

import re
from dataclasses import dataclass

VOICE_LINE_RE = re.compile(r"^(.+)\s+(\S+)\s+#.*$")
MANDARIN_VOICES = {
    "zh_CN": ("tingting", "tiantian"),
    "zh_TW": ("meijia",),
}


@dataclass(frozen=True)
class MacSpeechVoice:
    name: str
    lang: str


def parse_voice_line(line: str) -> MacSpeechVoice | None:
    if match := VOICE_LINE_RE.match(line):
        return MacSpeechVoice(match.group(1).strip(), match.group(2))
    return None


def voice_preference(name: str, lang: str) -> tuple[int, int]:
    """Prefer standard Mandarin voices over the alphabetical novelty voices.

    Some macOS versions expose quality labels in voice names. Prefer a labeled
    Premium/Enhanced variant when available, without requiring a download.
    Other languages and unrecognized voices retain their discovery order.
    """
    preferred = MANDARIN_VOICES.get(lang, ())
    family = name.split(" (")[0].replace("-", "").casefold()
    if family not in preferred:
        return (3, 0)
    quality = (
        0
        if "(premium)" in name.casefold()
        else 1
        if "(enhanced)" in name.casefold()
        else 2
    )
    return (quality, preferred.index(family))
