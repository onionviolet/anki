# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import runpy
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.mark.parametrize(
    "text,options,expected_voice",
    [
        ("你好，世界。", [], "Tingting (Chinese (China mainland))"),
        ("你好，世界。", ["--lang", "zh-TW"], "Meijia"),
        ("你好，世界。", ["--voice", "Meijia"], "Meijia"),
        (
            "你好，世界。",
            ["--voice", "Eddy (Chinese (China mainland))"],
            "Eddy (Chinese (China mainland))",
        ),
        ("你好，世界。", ["--lang", "system"], None),
        ("Hello, world.", [], None),
        ("日本語です。", [], None),
    ],
)
def test_local_speech_selects_mandarin_or_honors_explicit_voice_and_language(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    text: str,
    options: list[str],
    expected_voice: str | None,
) -> None:
    script = runpy.run_path(
        str(Path(__file__).parents[2] / "integrations/local_speech.py")
    )
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    monkeypatch.setattr(Path, "is_file", lambda _: True)
    monkeypatch.setattr(
        "sys.argv", ["local-speech", text, str(tmp_path / "speech.wav"), *options]
    )
    run = MagicMock(
        return_value=MagicMock(
            stdout="""Eddy (Chinese (China mainland)) zh_CN # 你好！
Tingting (Chinese (China mainland)) zh_CN # 你好！
Meijia zh_TW # 你好！
"""
        )
    )
    monkeypatch.setattr("subprocess.run", run)

    script["main"]()

    command = run.call_args.args[0]
    if expected_voice:
        assert command[command.index("-v") + 1] == expected_voice
    else:
        assert "-v" not in command
    assert command[-1] == text


def test_local_speech_rejects_unavailable_language_before_generating_audio(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    script = runpy.run_path(
        str(Path(__file__).parents[2] / "integrations/local_speech.py")
    )
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    monkeypatch.setattr(Path, "is_file", lambda _: True)
    monkeypatch.setattr(
        "sys.argv",
        ["local-speech", "你好", str(tmp_path / "speech.wav"), "--lang", "zh_CN"],
    )
    run = MagicMock(return_value=MagicMock(stdout="Samantha en_US # Hello!"))
    monkeypatch.setattr("subprocess.run", run)

    with pytest.raises(SystemExit) as error:
        script["main"]()

    assert error.value.code == 2
    assert run.call_count == 1
