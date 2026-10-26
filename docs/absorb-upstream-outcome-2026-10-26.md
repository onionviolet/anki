# Anki upstream absorption outcome, October 26, 2026

Level of work: fork and maintenance (smallest diff, upstream structure kept, departures listed below). Overnight pass, run by Claude Sonnet 5.5. Nothing pushed, installed or deleted; no wheels built; the real profile was not touched.

## State

- Absorb branch: `weibao/absorb-2026-10-26`, cut from `weibao/integrate-2026-10`. Merge of `upstream/main` (34 commits, HEAD of upstream fetched 2026-10-26 `1b48429de`). Now 0 commits behind upstream.
- Protection: `~/.local/share/codex-recovery/anki-weibao-2026-10-26/` holds `local-heads.bundle` (all local branches and tags, verified), `untracked.tar` and `dirty.diff`. A bundle of remote-tracking refs failed (`--all` needs blobs the partial clone does not hold), so those refs are not in it; they live on the remotes.
- Dirty work: the 21 dirty files were the October 13 absorb (D2/D3/D4, docs, release notes, portable-rules sync). Coherent, so committed alone as `e529d5c48` on `weibao/integrate-2026-10`. (The first version carried a Co-Authored-By trailer against the user's global rule; amended before anything else was built on it.)

## Merge conflicts and decisions

| File | Resolution |
| --- | --- |
| `README.md`, `rslib/src/scheduler/fsrs/simulator.rs` | Fork side kept. Upstream's simulator change was only the `rand` 0.10 call rename inside a function the fork had rewritten. |
| `ts/lib/tslib/help-page.ts` | Upstream side (new `/manual/...` docs URLs); fork had no entries of its own there. |
| `CONTRIBUTORS`, `rslib/src/storage/card/mod.rs` (test imports) | Union of both sides. |
| `qt/tests/test_utils.py` | Both sides kept: fork's three tests plus upstream's menu-shortcut test (uses the existing `qapp` fixture). |
| `Cargo.lock`, `cargo/licenses.json` | Regenerated, see below. |

## Departures from upstream, recorded

1. Upstream moved `rand` to 0.10 and `zip` to 9. Fork-only code broke and was adapted minimally: `rslib/src/import_export/package/meta.rs` (`file_names()` now yields `Result`), `colpkg/export.rs` (`RngCore` is now `Rng`), `colpkg/tests.rs` (`ZipFile::name()` is a `Result`), `storage/deck/mod.rs` tests (`Rng` is now `RngExt`).
2. `Cargo.lock` started from upstream's, then `cargo update` bumped `rustls-webpki`, `webpki-roots`, `tokio` (1.51.6, the smallest patched version) and `ammonia` (4.2.4) because cargo-deny flagged advisories published after upstream's lock (RUSTSEC-2026-0346 to 0349, 0381, 0382, 0386 and ammonia's). `cargo/licenses.json` regenerated with `just fix-minilints`.
3. Two fork-side test and type issues that the merge exposed, neither caused by upstream code: `qt/tests/test_cram_mode.py` imported `aqt.deckbrowser` before a backend existed (now imports with translation stubbed, the pattern `test_deckbrowser.py` uses), and `qt/aqt/browser/table/model.py` slice typing failed the newer mypy 2.3.1 that `uv sync` pulled in (row loop instead of slicing).

## JSchoreels (step 4)

Fetched: `jschoreels/main` is 87 non-merge commits ahead (`96af4ca9d`, build 107), 484 files, almost entirely the RWKV model line (SM36/SM40/SM55/SM56 defaults, state precision, portable updater, schedule copying) plus two queue commits. The October 13 prompt and outcome scoped only the interday-priority fix (done, `d77ef5c87`) and explicitly left the newer RWKV work as a future batch with wider dependency ranges. Nothing further absorbed, so as not to transplant part of it. Candidates that touch the code D3 already ported, for the next scoped batch: `6cd4ca9f0` (before/after/mixed intraday ordering), `4d1051fe3`, `e3599ef5c` (learn-ahead limits with FSRS sorting).

## Verification

- `just check` passed on the final commit `1ad297166` (Build succeeded). It was run five times, not once: runs 1 to 4 each stopped at a real defect listed above (stale licenses.json, advisory failures, build break from rand/zip, rustfmt, cram test collection plus mypy). Pytest in that final run: 1,197 Qt tests passed, 6 skipped; vitest 34 files passed. The runs shared the machine with other sessions' builds (load average above 100 per the coordinator), so treat slow timings as contention. One earlier vitest run timed out a hook in `reviewer/mathjax.test.ts` (10 s) under load and passed on the next run.
- Fork additions verified present: `qt/aqt/weibao/cram_mode.py`, deck-list Cram button commit `7f8ea7ff8`, cram + sidebar commit `a83b5ec12` and Qwen commit `bc15ff5af` are ancestors; the files for Qwen speech (`integrations/qwen_tts/*`, `integrations/local_speech.py`, `pylib/anki/_qwen_tts_worker.py`), the Browse sidebar test and the cram/Qwen/local-speech tests are byte-identical to the pre-merge tree.
- Not done: Rust test suite (`just test-rust`), e2e, wheels, installed candidate, human acceptance. `just check` compiles Rust and the Python/TS tests only.

## Remaining gate

Wheels build plus a disposable-profile launch of the merged branch, as in the October 13 flow, before installing. Then merge decision.

## Proposals (not accepted decisions)

- P1: JSchoreels RWKV batch on its own branch: SM56 default model, state precision, portable updater, in dependency order, with the October 13 backend probe as the regression bar.
- P2: First slice of P1: `6cd4ca9f0` + `e3599ef5c` queue ordering fixes, since they extend code already ported.
- P3: Add `just test-rust` to the pre-merge routine for upstream absorbs; this pass changed `rand`/`zip` APIs and only compile-checked the Rust tests.

## Questions for Weibao

- Q1: Start P1/P2 (large RWKV absorb)?
- Q2: Accept the lock-file security bumps (tokio 1.51.6, ammonia 4.2.4, rustls-webpki, webpki-roots) as the fork's baseline, or prefer a different pin?
- Q3: Merge `weibao/absorb-2026-10-26` into `weibao/integrate-2026-10`, and push when you choose.

## Resume note

Stopped 03:35 EDT, well before 07:30. Nothing in flight. Resume at the remaining gate: run `just test-rust`, then `just wheels`.
