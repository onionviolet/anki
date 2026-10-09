# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from unittest.mock import MagicMock

import pytest

from anki.sound import TTSTag
from aqt.tts import MacTTSFilePlayer, MacTTSPlayer

VOICE_LIST = """Eddy (Chinese (China mainland)) zh_CN # 你好！
Eddy (Chinese (Taiwan)) zh_TW # 你好！
Sinji zh_HK # 你好！
Tingting (Chinese (China mainland)) zh_CN # 你好！
Ting-Ting (Enhanced) zh_CN # 你好！
Ting-Ting (Premium) zh_CN # 你好！
Meijia zh_TW # 你好！
Samantha en_US # Hello!
"""


@pytest.mark.parametrize("player_type", [MacTTSPlayer, MacTTSFilePlayer])
@pytest.mark.parametrize(
    "lang,requested,expected",
    [
        ("zh_CN", [], "Apple_Ting-Ting_(Premium)"),
        ("zh_TW", [], "Apple_Meijia"),
        ("zh_HK", [], "Apple_Sinji"),
        (
            "zh_CN",
            ["Apple_Eddy_(Chinese_(China_mainland))"],
            "Apple_Eddy_(Chinese_(China_mainland))",
        ),
        ("zh_CN", ["Missing_voice"], "Apple_Ting-Ting_(Premium)"),
        ("zh_CN", ["Apple_Meijia"], "Apple_Ting-Ting_(Premium)"),
    ],
)
def test_mac_tts_selects_preferred_mandarin_without_overriding_requests(
    monkeypatch: pytest.MonkeyPatch,
    player_type: type[MacTTSPlayer],
    lang: str,
    requested: list[str],
    expected: str,
) -> None:
    monkeypatch.setattr(
        "aqt.tts.subprocess.run", lambda *args, **kwargs: MagicMock(stdout=VOICE_LIST)
    )
    player = player_type(MagicMock())

    match = player.voice_for_tag(TTSTag("你好", lang, requested, 1.0, []))

    assert match is not None
    assert match.voice.name == expected


@pytest.mark.parametrize(
    "voice_list,expected",
    [
        ("Eddy zh_CN # 你好！\nTingting zh_CN # 你好！", "Apple_Tingting"),
        ("Eddy zh_CN # 你好！\nTian-Tian zh_CN # 你好！", "Apple_Tian-Tian"),
        ("Eddy zh_CN # 你好！", "Apple_Eddy"),
    ],
)
def test_mac_tts_uses_installed_fallback_when_quality_variants_are_absent(
    monkeypatch: pytest.MonkeyPatch, voice_list: str, expected: str
) -> None:
    monkeypatch.setattr(
        "aqt.tts.subprocess.run", lambda *args, **kwargs: MagicMock(stdout=voice_list)
    )
    player = MacTTSPlayer(MagicMock())

    match = player.voice_for_tag(TTSTag("你好", "zh_CN", [], 1.0, []))

    assert match is not None
    assert match.voice.name == expected


def test_mac_tts_does_not_substitute_another_region_when_language_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "aqt.tts.subprocess.run",
        lambda *args, **kwargs: MagicMock(stdout="Meijia zh_TW # 你好！"),
    )

    assert (
        MacTTSPlayer(MagicMock()).voice_for_tag(TTSTag("你好", "zh_CN", [], 1.0, []))
        is None
    )


def test_mac_tts_honors_subclass_voice_regex() -> None:
    import re

    class CustomPlayer(MacTTSPlayer):
        VOICE_HELP_LINE_RE = re.compile(r"^([^|]+)\|([^|]+)$")

    voice = CustomPlayer(MagicMock())._parse_voice_line("Custom Voice|zh_CN")
    assert voice is not None
    assert voice.original_name == "Custom Voice"
    assert voice.lang == "zh_CN"
