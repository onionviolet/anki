# Local Qwen Mandarin speech

This optional engine uses the free local **Qwen3-TTS 1.7B CustomVoice 4-bit** model through MLX-Audio on Apple Silicon. It does not import MLX into Anki, replace existing media, or change card fields or scheduling. After setup downloads, generation runs with Hugging Face and Transformers offline flags enabled.

## Setup and use

Run from the repository root:

```sh
just qwen-setup
just qwen-speech '你好。银行。重庆。音乐。' /tmp/qwen-preview.wav
just qwen-speech '你好。银行。重庆。音乐。' /tmp/qwen-serena.wav Serena
just qwen-speech '你好。银行。重庆。音乐。' /tmp/qwen-slow.wav Vivian 0.85
```

Setup creates a separate environment under `~/Library/Application Support/AnkiQwenTTS`, downloads the pinned approximately 2.3 GB model into the normal Hugging Face cache, checks its loader and then publishes `config.json`. An interrupted setup does not enable an incomplete runtime. `installed-requirements.txt` records the resolved environment. `ANKI_QWEN_TTS_ROOT` can select another runtime/config/cache root for an isolated instance. Restart the updated fork after setup so its audio players rediscover the runtime.

In a card template, select a voice explicitly:

```html
{{tts zh_CN voices=Qwen3_Vivian:Simplified}}
{{tts zh_CN voices=Qwen3_Serena speed=0.85:Example}}
{{tts zh_CN voices=Qwen3_Uncle_Fu:Simplified}}
```

Configured Qwen is also preferred for unqualified `{{tts zh_CN:Field}}` tags. Explicit voice preferences keep their order across engines. A tag explicitly requesting Apple Tingting will continue using Apple until its voice list is changed. To retain a native fallback on clients without Qwen, place `Qwen3_Vivian` before the existing Apple voice names in that list. Safe mode skips Qwen. This integration exposes only mainland Mandarin `zh_CN`, not a separately verified Taiwan accent.

The existing daily profile's templates were not changed during this implementation, and the updated fork has not been installed over the daily Anki app. WAV export can be used immediately through **Study tools → Capture → Choose local audio**, with preview before acceptance. Template changes belong in the updated fork or another client that actually has this engine; ordinary Anki does not gain a new TTS engine just by naming it in a template.

## Playback and cache behavior

Generation runs on a background thread through a persistent isolated Python worker. New clips use the selected Chinese preset voice and a fixed seed. The short style instruction requests clear, steady standard Mandarin with a neutral tone. Sampling uses temperature 0.7, top-k 50, top-p 1.0 and repetition penalty 1.05. These delivery controls do not guarantee against additions, omissions or pronunciation errors. The exact field text is passed separately from the style instruction; there is no chat model rewriting or reasoning stage. This is not a pinyin/phoneme override engine; intended polyphonic readings still require listening checks.

Clips are cached under the runtime's `audio` directory by model path/revision, MLX-Audio version, text, voice, speed, instruction and all generation settings. Changing the reading profile regenerates audio without deleting older files. Valid cached clips replay without starting a model process. A worker stays warm after generation until interrupted or the profile closes. Cancelling a generation terminates that worker; another uncached request can start a fresh one. Profile close releases the process and drops its late result. Generation errors finish the queue and display an error instead of leaving playback stuck. Generation is limited to 10 tokens per letter/digit plus 32 tokens of padding, with a 64-token minimum and 4,096-token maximum. At approximately 12.5 frames/second this allows roughly five seconds for a short word, with generous time for longer readings. Reaching the limit rejects the clip rather than caching and playing a partial reading. This detects gross overruns, not transcript mismatches.

Speed is limited to 0.5–2.0 and uses pitch-preserving time stretching. Input is limited to 2,000 characters, with a five-minute generation timeout. Output is mono 24 kHz PCM WAV, written atomically. A partial or truncated cache entry is regenerated. The export recipe refuses an existing output file. Generated clips stay outside collection media until explicitly imported, so they do not automatically sync to other clients.

## Provenance and validation

- Model: [`mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-4bit`](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-4bit), revision `f35faf19b0cc2160865af64ecf0f22f83d335135`, Apache-2.0. The underlying [Qwen model](https://github.com/QwenLM/Qwen3-TTS) provides the preset Chinese voices.
- Runtime: [MLX-Audio](https://github.com/Blaizzy/mlx-audio) 0.5.7. Version 0.5.8 was inside the repository's seven-day dependency cooldown at implementation time, so 0.5.7 was selected. The external environment also uses librosa 0.11.0 for speed changes.
- The adapter, worker, setup and probes are original fork code. Model weights and third-party runtime packages are not bundled in Anki wheels.

`just test-py-target --import-mode=importlib pylib/tests/test_qwen_tts.py qt/tests/test_qwen_tts_player.py` passed 20 tests covering cache reuse/identity, validation, corrupt audio, missing setup, engine preference, cancellation, profile shutdown and error completion. Importlib mode is needed when targeting both test package trees in one pytest invocation.

`just qwen-runtime` passed real offscreen reviewer playback on a fresh synthetic profile, with a separate runtime cache. The card renderer produced the requested Qwen tag, MPV completed playback, and Qt's heartbeat continued during generation. In the final source run, first generation plus playback took 9.27 seconds; cached playback took 2.54 seconds. Those measure this short synthetic sentence on this Mac, not general latency or pronunciation accuracy. The warm process was reused; cancelling generation and switching profiles released it and discarded late audio. A separate safe-mode launch did not register Qwen.

The generated `out/qwen-mandarin-preview.wav` is a 13.44-second Vivian pronunciation sample. No listening acceptance or claim of fully correct tones follows from generation or these tests. Reproduce the runtime gate with `just qwen-runtime`; its temporary base path contains the full application logs and report.

`just check` passed after the final worker import fix. The verified source slices include 226 pylib tests, 1,191 Qt tests (6 skipped) and 1,194 Rust tests (13 skipped), with formatting, typing and lint checks. Unchanged targets reused their passing stamps on the final incremental run. The required repository format gate also corrected an existing table alignment in the earlier integration review without changing its text or hashes.

`just wheels` built both desktop wheels. Archive bytes for `anki/qwen_tts.py`, `anki/_qwen_tts_worker.py`, `aqt/weibao/qwen_tts.py` and `aqt/sound.py` match the final source exactly. Packaging does not install the fork or modify existing templates. Vivian and slower Serena WAV exports both succeeded; installed-app and human pronunciation acceptance remain separate.
