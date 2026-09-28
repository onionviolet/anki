# Personal Anki fork

This fork combines [Ankitects Anki](https://github.com/ankitects/anki) 26.09.3 with the experimental FSRS7/RWKV work from [JSchoreels/anki](https://github.com/JSchoreels/anki) and the study tools below. FSRS7 and RWKV change scheduling when enabled. RWKV is desktop-only; other clients continue using their supported scheduler. Back up a collection before enabling experimental scheduling.

The imported UI work includes simulator workload comparisons, clearer limited deck counts, the current-deck Browser search, and fixes for IME text committed while an editor field closes. The imported build also supports an isolated portable app. The bundled AnkiConnect server retains the official application version to avoid the FSRS7 fork's version-suffix parsing issue.

## Included feature

Right-click a card during review and choose **Mark for repair**. The menu records either **Bad explanation** or **Confused with another card** as a note tag containing the exact card ID. The marker syncs with the collection and does not change review scheduling. Search `tag:weibao::repair::*` in the browser to find marked notes.

The feature lives in `qt/aqt/weibao/review_capture.py` and uses Anki's reviewer hook and collection tag operation. Safe mode skips it.

## Study bridge

The first-party [`ankictl`](https://github.com/onionviolet/ankictl) client is included in `integrations/ankictl/` and packaged as a standalone `ankictl` console command in the desktop Python wheel. Run `just bridge ping` to check its connection, or `just bridge repair --json` to list reviewer repair markers. The pinned source and license are recorded in `integrations/ankictl/SOURCE.md`.

The fork also bundles the AnkiConnect v6 server in `qt/aqt/weibao/ankiconnect_vendor/`. It starts when a profile opens and stops when the profile closes. If the profile base already contains the AnkiConnect add-on (`2055492159`), the bundled server stays off so the installed add-on retains its settings and owns the port. Safe mode skips both fork additions. The bundled server binds to `127.0.0.1:8765` by default. An optional `weibao_ankiconnect.json` file in the profile folder can override AnkiConnect settings, including `apiKey` and `webBindPort`; `ANKICONNECT_BIND_PORT` is available for an isolated test instance. The vendored source, license, and exact upstream revision are recorded in `qt/aqt/weibao/ankiconnect_vendor/SOURCE.md`.

No collection content, review history, profile paths, or credentials belong in this repository.

## Optional Chinese Support 3

The fork bundles the pinned Chinese Support 3 add-on from `integrations/chinese-support-3`. On launch outside safe mode, it copies the add-on into the active Anki base if that add-on is absent, then Anki loads it normally. An existing installed copy and its configuration win. See `integrations/CHINESE_SUPPORT3.md` for the source, license, and boundaries. The fork does not enable its field filling on a note type or alter the existing `Mandarin Merged` tone display.

## Local verification

The merge was validated in an isolated worktree. `just check` passed with the repository's `CONTRIBUTORS_BYPASS_EMAILS` setting for this fork author: 1,111 Rust tests, 741 Qt tests, 200 pylib tests, and the web build, format, type, and lint checks. `just test-e2e` finished with 38 passed and one skipped. `just portable` produced a macOS archive containing the Rust bridge, `ankictl`, AnkiConnect, Chinese Support source, and RWKV assets. The archive was extracted and launched with an isolated profile, but native first-run verification could not finish while the Mac was locked. This build has not been installed over the daily Anki app or tested against its collection.
