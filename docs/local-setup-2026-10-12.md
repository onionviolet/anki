# Air mirror restoration on the Pro, October 12, 2026

## Restored profile

The Air profile had been archived rather than activated. Copied the complete `~/MacTransferArchive/AppData-from-Air-20261012/Anki2` tree to `~/Library/Application Support/Anki2`. The destination did not exist. SHA-256 comparison of all 40 files found zero mismatches; the archive remains intact. A separate temporary database copy passed SQLite `quick_check` with the required `unicase` collation registered.

The copied collection contains 48,897 cards, 24,952 notes, 38 decks and 322 review-log rows. Its media folder contains three images; there are no saved `[sound:...]` references in note fields. The AnkiConnect add-on and settings were preserved. This establishes equality to the transferred snapshot, not to changes made on the Air after transfer.

## Installed fork

`~/Applications/Anki Weibao.app` launches the newly built 26.9.3 desktop wheels in `~/Library/Application Support/AnkiWeibao/venv`. The launch script uses absolute paths, clears `PYTHONPATH`, disables developer mode and remote debugging, and writes logs to `~/Library/Logs/AnkiWeibao/application.log`. It uses the standard local profile location. The existing `/Applications/Anki.app` remains installed.

Restored the missing pinned Python 3.13.13 interpreter and installed `just` and Ninja under `~/.local/bin` through the bundled uv. The repository's Rust 1.99.0 toolchain is available. Matching runtime dependencies were copied from the verified mirrored development environment after the Qt downloads stalled; uv checked the final package set for compatibility. The installed environment uses the runtime versions selected by `uv.lock`, recorded in `~/Library/Application Support/AnkiWeibao/runtime-requirements.txt`. Wheel SHA-256 values are recorded in `installed-wheels.json` beside it. No Homebrew installation was needed.

## Verification

- `just build` passed.
- `just check` passed: the current invocation ran 226 pylib, 1,191 Qt (6 skipped), and 187 TypeScript tests, plus formatting, lint and type checks. Other unchanged targets reused existing build/test stamps; this is not a claim of a fresh complete Rust test run.
- `just wheels` passed and installed both 26.9.3 wheels. `uv pip check` passed for all 39 installed packages.
- `QT_QPA_PLATFORM=offscreen just study-runtime` passed the synthetic application workflow and safe mode, including Study tools, repair/capture/break operations, Undo, AnkiConnect and MPV completion.
- The actual installed app launcher passed a separate offscreen smoke test against a disposable copy of the restored profile: deck browser state, 48,897 cards, 24,952 notes, 38 decks, Study tools and the Qwen module. The smoke test closed cleanly. It did not test on the active profile.

Evidence is saved outside Git under `~/Library/Application Support/AnkiWeibao/setup-evidence`. Existing uncommitted source work was preserved. No commit or push was made.

## Migration considerations

The profile has no AnkiWeb sync key. Local study works; cross-device syncing still requires the user's sign-in. AnkiWeb supports synchronization of collections and media across devices. If a first-sync upload/download choice appears, choose only after comparing which side has the desired data: downloading replaces local changes, while uploading replaces the remote collection. See [Anki's syncing manual](https://docs.ankiweb.net/manual/syncing).

The Mandarin Merged templates explicitly select Apple Tingting. That voice is installed on the Pro; the existing templates and scheduler configuration were preserved. Collection-wide FSRS is currently disabled in the transferred profile. Experimental scheduler selection remains a separate user decision.

Qwen's pinned model and separate MLX environment are installed under `~/Library/Application Support/AnkiQwenTTS`. The first download route stalled; `HF_HUB_DISABLE_XET=1 just qwen-setup` completed through HTTP and verified the model loader. `QT_QPA_PLATFORM=offscreen just qwen-runtime` passed actual reviewer generation, MPV completion and a responsive UI heartbeat (10.33 seconds for the synthetic first generation/playback), exact WAV cache reuse (2.55 seconds), cancellation/profile-close cleanup, and safe mode. Explicit Apple voice choices remain unchanged. Human pronunciation acceptance remains open.

The app was launched normally through macOS LaunchServices with the restored `User 1` profile and remains open. Its AnkiConnect v6 API returned 48,897 cards, 24,952 notes and 38 decks. The process uses the installed fork environment and standard active profile path. Human visual acceptance remains open; no cloud sync, review answer or note edit was performed.
