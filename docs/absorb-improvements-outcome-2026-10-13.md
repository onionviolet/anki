# Anki absorption outcome, October 13, 2026

## Scope and current state

The prompt-review roundtrip completed in a separate ordinary ChatGPT chat. Its response was captured in full, reconciled with local evidence and user authorization, and used to continue implementation in the existing Codex chat. The reviewer did not inspect this repository. The executable prompt remains `docs/absorb-improvements-prompt.md`; the raw review and reconciliation are saved beside it.

Source changes, checks, wheel packaging and the isolated installed candidate are verified. The user authorized normal closure; the verified wheels were installed into the active environment and the real launcher was reopened. No cloud sync, personal note/template/scheduler change, commit or push occurred.

Baseline HEAD: `2e8c5fcb0`. Branch: `weibao/integrate-2026-10`. Pre-existing tracked changes and untracked Qwen work were preserved; a recovery snapshot is at `/private/tmp/anki-integration-2026-10-13-baseline`. The current profile was not used for tests.

## Implemented batch

| Decision | Problem and resulting behavior | Source |
| --- | --- | --- |
| D2 | A missing or filtered template deck override sent new cards to Default. Generation now checks the override, then the selected normal deck, then Default. This also fixes capture/add-on paths using normal card generation. | Official Anki [#5544](https://github.com/ankitects/anki/pull/5544), commit [`7a27a76066ade54ec4df6d10a2574fc6fd27999e`](https://github.com/ankitects/anki/commit/7a27a76066ade54ec4df6d10a2574fc6fd27999e) |
| D3 | Exact FSRS retrievability sorting ignored Before/After priority for interday learning cards. Admission still uses the shared ordering and limits; presentation now groups admitted interday cards according to the existing setting. Intraday ordering, new-card mixing, current-card preservation and counts are retained. | JSchoreels [`d77ef5c87b52c3b2a872a984ee68686f68e81291`](https://github.com/JSchoreels/anki/commit/d77ef5c87b52c3b2a872a984ee68686f68e81291) |
| D4 | Short help paragraphs could occupy the same row. Each paragraph now occupies its own row, with the globe icon's paragraph remaining beside the icon. | Official Anki [#5801](https://github.com/ankitects/anki/pull/5801), commit [`dd324c8acc3d61f7f2696ea6b9f26bf2b494ca45`](https://github.com/ankitects/anki/commit/dd324c8acc3d61f7f2696ea6b9f26bf2b494ca45) |

The code is absorbed as patches without creating commits. Existing fork behavior is retained. Source attribution uses the existing AGPL/contributor model; the new upstream contributor entry was retained. RELEASE.md, the interday-learning Fluent help, architecture documentation and manual explain the behavior. A supporting `just test-e2e-target` recipe allows a focused Playwright rerun through the project's normal tooling.

## Sources considered and disposition

Remotes were freshly fetched. Official upstream was at `2f62b5e678079a4b163ec4f38cf0f8a7ea949852`; JSchoreels main was at `fb7876ea9ae8e9cb2350e244c3dd6baf24d63457`; origin had no new commits beyond local HEAD.

| Source or candidate | Evidence and disposition |
| --- | --- |
| Official Anki | Five commits absent by ancestry. Selected the concrete card-generation and help-layout fixes. Dependency upgrade and broad documentation-link churn are outside this behavior-focused batch. |
| JSchoreels | Selected the self-contained interday queue fix whose source base matches the local queue implementation. Newer RWKV reset, precision, cache, calibration and schedule-copying work has broader dependency ranges; it remains a future batch rather than being partially transplanted. |
| [Clanki](https://github.com/Expertium/Clanki), fetched main `d70b338077880fadbf26d12e52f856d6ab1ae2dc` | Inspected history and representative preset-memory-state/Change Deck performance ports (`723096d86`, `aa99c4949`). Their main mechanisms have already been imported through the earlier JSchoreels/Clanki absorption; no duplicate port was added. This does not claim that every Clanki change is present. |
| [Later-only rescheduling #5764](https://github.com/ankitects/anki/pull/5764) | GitHub API reported open, unmerged, head `a1a8961a0cc4625c43003a2d2618d4b313a29ae8`. Deferred: it is a new rescheduling operation requiring explicit UI semantics and FSRS7/RWKV compatibility evidence. |
| [FSRS Helper](https://github.com/open-spaced-repetition/fsrs4anki-helper), HEAD `29208f220f21ff994c199712a6aaac47636773bf` | Reviewed sibling dispersion and automatic-review configuration. Its config documentation warns that automatic dispersion on review can rebuild queues and disturb display ordering. Deferred until a dedicated preview/apply/Undo design can demonstrate compatibility. Existing planned-break tools are retained. |
| [Chinese Support](https://github.com/Gustaf-C/anki-chinese-support-3), HEAD `d2bc424f68a78294cd7607cb61b071ea5c92b319` | The bundled pin matches remote HEAD. No new source integration was necessary. |
| [Yomitan](https://github.com/yomidevs/yomitan) | Reviewed its dictionary/capture role. Existing AnkiConnect and previewed Capture remain the integration route. Browser extension/dictionary setup is separate from these core fixes. |
| Hourly statistics UI | Backend support already exists. A new visualization is a product/UI feature rather than a correctness patch; deferred rather than assuming backend availability establishes a useful finished interface. |

This is a bounded source comparison, not a complete ecosystem survey. No new optional add-on, browser extension, model or service was installed during absorption.

## Verification

- Before/after synthetic backend probe: old installed build reproduces wrong-deck generation and ignored interday priorities. Source and packaged candidate pass selected-deck generation and all nine combinations of three FSRS review orders with three learning-mix settings. The probe uses newly created temporary collections only.
- `just test-rust`: 1,197 tests passed, 13 skipped. Imported regressions cover override fallbacks, FSRS6/7 priorities, current-card preservation, queue counts, daily-limit admission and new-card mixing.
- `just check`: passed after correcting the prior roundtrip provenance JSON's indentation. Across the source gate, 226 pylib, 187 TypeScript and 1,191 Qt tests passed (6 Qt skipped), with formatting, types and lint. The final incremental run reused unchanged target stamps; Rust is independently fresh as recorded above.
- `QT_QPA_PLATFORM=offscreen just test-e2e`: 47 existing tests passed, 1 skipped. The additional temporary layout probe initially failed on an ambiguous locator after its paragraph check passed. Correcting the probe and running `just test-e2e-target absorption-help-smoke.spec.ts` passed paragraph separation and globe alignment. The temporary test source and screenshot were saved with evidence, then removed from the repository.
- `QT_QPA_PLATFORM=offscreen just study-runtime`: full synthetic Study tools workflows, AnkiConnect, repair/capture/break/Undo, MPV completion, profile switching and safe mode passed.
- `just wheels`: both 26.9.3 wheels built. Candidate dependency compatibility passed for all 39 packages. The isolated installed candidate reached deckBrowser with 48,897 cards, 24,952 notes, 38 decks, Study tools and the Qwen module on a disposable profile copy. The copied AnkiConnect add-on uses its own port, and network update checks are disabled only in that temporary profile. The corrected candidate run exited normally.
- Both candidate and rollback environments load the Rust backend. Qwen source and template choices were not changed in this batch; previous Qwen audio evidence remains scoped to that unchanged implementation, not a new pronunciation acceptance claim.

Evidence: `~/Library/Application Support/AnkiWeibao/setup-evidence/absorption-2026-10-13`.

Candidate wheels, environment and source/package manifest: `~/Library/Application Support/AnkiWeibao/candidates/2026-10-13`.

Rollback: `~/Library/Application Support/AnkiWeibao/rollbacks/2026-10-13-before-absorption`. It preserves the previous environment, dependency record and installed wheel hashes.

## Installed outcome

The normal API quit request was blocked by an updater offer. The offer was declined and Anki exited via its normal application-menu Quit action. The saved candidate wheel hashes were verified and both packages were reinstalled without changing dependencies. All 101 packaged anki files and 359 packaged aqt files match their candidate wheels; all 39 dependency packages remain compatible. The installed version remains 26.09.3, with the source/package manifest identifying this local patch set.

The real macOS launcher reopened User 1. AnkiConnect reported 48,897 cards, 24,952 notes and 38 decks, exactly matching the immediately pre-install counts. The native deck list was checked and its screenshot saved with evidence. An additional updater offer/download for JSchoreels build 102 was declined; final package bytes still match our validated candidate. No alternate release was installed.

The rollback environment remains at the path above. The current app is open and ready for study. No required installation gate remains. Human assessment of the changes and pronunciation remains distinct from automated verification.
