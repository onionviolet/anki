# Copyright: Ankitects Pty Ltd and contributors
# Copyright: Weibao Chen
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import io
import json
import sys
import threading
import wave
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from anki.qwen_tts import (
    GENERATION_SETTINGS,
    INSTRUCTION,
    MLX_AUDIO_VERSION,
    QwenCancelled,
    QwenRuntime,
    QwenWorker,
    generation_token_limit,
    valid_audio,
)


@pytest.fixture
def runtime(tmp_path: Path) -> QwenRuntime:
    return QwenRuntime(
        tmp_path / "python", tmp_path / "model", "revision-a", tmp_path / "audio"
    )


def write_audio(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(b"\x01\x00" * 2400)


def test_qwen_cache_reuses_audio_without_starting_worker(
    runtime: QwenRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = runtime.audio_path("你好", "Vivian", 1.0)
    write_audio(path)
    worker = QwenWorker(runtime)
    start = MagicMock(side_effect=AssertionError("Cache replay started the model"))
    monkeypatch.setattr(worker, "_start", start)

    assert worker.generate("你好") == path
    start.assert_not_called()


def test_qwen_cache_separates_text_speaker_speed_and_model_revision(
    runtime: QwenRuntime,
) -> None:
    paths = {
        runtime.audio_path("你好", "Vivian", 1.0),
        runtime.audio_path("你好！", "Vivian", 1.0),
        runtime.audio_path("你好", "Serena", 1.0),
        runtime.audio_path("你好", "Vivian", 0.8),
        replace(runtime, revision="revision-b").audio_path("你好", "Vivian", 1.0),
    }
    assert len(paths) == 5


def test_qwen_cache_regenerates_after_reading_settings_change(
    runtime: QwenRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = runtime.audio_path("你好", "Vivian", 1.0)
    write_audio(original)
    monkeypatch.setitem(GENERATION_SETTINGS, "temperature", 0.6)
    updated = runtime.audio_path("你好", "Vivian", 1.0)
    assert original != updated
    assert not valid_audio(updated)


def test_qwen_worker_keeps_text_separate_and_rejects_unfinished_speech(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from anki import _qwen_tts_worker as worker

    output = tmp_path / "unfinished.wav"
    text = "使用。银行。重庆。"
    request = {
        "text": text,
        "speaker": "Vivian",
        "speed": 1.0,
        "instruction": INSTRUCTION,
        "generation": GENERATION_SETTINGS,
        "max_tokens": generation_token_limit(text),
        "output": str(output),
    }
    model = MagicMock()
    segment = MagicMock(sample_rate=24000, token_count=request["max_tokens"])
    model.generate_custom_voice.side_effect = lambda **_: iter([segment])
    mx = MagicMock()
    modules = {
        "mlx.core": mx,
        "numpy": MagicMock(),
        "mlx_audio.tts.utils": MagicMock(load_model=lambda _: model),
    }
    monkeypatch.setattr(worker.importlib, "import_module", modules.__getitem__)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(request) + "\n"))
    protocol = io.StringIO()
    monkeypatch.setattr(sys, "stdout", protocol)
    monkeypatch.setattr(sys, "argv", ["worker", "model"])

    worker.main()

    args = model.generate_custom_voice.call_args.kwargs
    assert args["text"] == text
    assert args["instruct"] == INSTRUCTION
    assert args["speaker"] == "Vivian"
    assert args["temperature"] == GENERATION_SETTINGS["temperature"]
    assert args["max_tokens"] < 4096
    assert model.generate_custom_voice.call_count == 3
    assert "did not finish reading" in json.loads(protocol.getvalue())["error"]
    assert not output.exists()


def test_qwen_limits_short_word_runaways_but_allows_longer_readings() -> None:
    assert generation_token_limit("使用") == 64
    assert generation_token_limit("使用。进步。我们每天学习中文。") == 152
    assert generation_token_limit("你" * 2000) == 4096


@pytest.mark.parametrize(
    "text,speaker,speed",
    [
        ("", "Vivian", 1),
        ("你" * 2001, "Vivian", 1),
        ("你好", "Unknown", 1),
        ("你好", "Vivian", float("nan")),
        ("你好", "Vivian", 0.4),
    ],
)
def test_qwen_rejects_invalid_request_before_spawning(
    runtime: QwenRuntime,
    monkeypatch: pytest.MonkeyPatch,
    text: str,
    speaker: str,
    speed: float,
) -> None:
    worker = QwenWorker(runtime)
    start = MagicMock()
    monkeypatch.setattr(worker, "_start", start)
    with pytest.raises(ValueError):
        worker.generate(text, speaker, speed)
    start.assert_not_called()


def test_qwen_cancelled_request_does_not_play_cached_audio(
    runtime: QwenRuntime,
) -> None:
    write_audio(runtime.audio_path("你好", "Vivian", 1.0))
    cancelled = threading.Event()
    cancelled.set()
    with pytest.raises(QwenCancelled):
        QwenWorker(runtime).generate("你好", cancelled=cancelled)


def test_qwen_rejects_worker_error_and_closes_process(
    runtime: QwenRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    worker = QwenWorker(runtime)
    process = MagicMock()
    worker._process = process
    process.poll.return_value = None
    monkeypatch.setattr(worker, "_start", lambda: process)
    monkeypatch.setattr(
        worker, "_response", lambda *args: {"error": "Model cannot load"}
    )

    with pytest.raises(RuntimeError, match="Model cannot load"):
        worker.generate("你好")

    process.stdin.close.assert_called_once()
    process.wait.assert_called_once()
    assert worker._process is None


def test_qwen_rejects_truncated_wav_cache(tmp_path: Path) -> None:
    path = tmp_path / "audio.wav"
    write_audio(path)
    assert valid_audio(path)
    path.write_bytes(path.read_bytes()[:-10])
    assert not valid_audio(path)


def test_qwen_runtime_requires_completed_setup(tmp_path: Path) -> None:
    assert QwenRuntime.read(tmp_path) is None
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "mlx_audio": MLX_AUDIO_VERSION,
                "python": str(tmp_path / "missing"),
                "model": str(tmp_path / "model"),
                "revision": "test",
            }
        )
    )
    with pytest.raises(ValueError, match="missing"):
        QwenRuntime.read(tmp_path)
