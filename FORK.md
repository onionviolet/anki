# Personal Anki fork

This fork keeps Anki's scheduler and collection format intact while adding small study tools to the desktop reviewer. The upstream project is [Ankitects Anki](https://github.com/ankitects/anki).

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

An isolated fork launch with a separate single-instance key, base folder, and API port returned AnkiConnect v6, one default deck, and zero notes through the bundled `ankictl` client. The `aqt` wheel contains the client, server source, and license. The Rust bridge loaded after rebuilding with Rust 1.98.1; Rust 1.97.1 generated a misaligned `LINKEDIT` string pool rejected by macOS 27, matching [rust-lang/rust#157750](https://github.com/rust-lang/rust/issues/157750). The fork pins 1.98.1. `just check` passed with the repository's `CONTRIBUTORS_BYPASS_EMAILS` setting for this fork author: 184 pylib tests, 130 Qt tests, 672 Rust tests, 71 TypeScript tests, and formatting, typing, and lint checks. The fork is not installed over the daily Anki app.
