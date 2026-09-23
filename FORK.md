# Personal Anki fork

This fork keeps Anki's scheduler and collection format intact while adding small study tools to the desktop reviewer. The upstream project is [Ankitects Anki](https://github.com/ankitects/anki).

## Included feature

Right-click a card during review and choose **Mark for repair**. The menu records either **Bad explanation** or **Confused with another card** as a note tag containing the exact card ID. The marker syncs with the collection and does not change review scheduling. Search `tag:weibao::repair::*` in the browser to find marked notes.

The feature lives in `qt/aqt/weibao/review_capture.py` and uses Anki's reviewer hook and collection tag operation. Safe mode skips it.

## Study bridge

The first-party [`ankictl`](https://github.com/onionviolet/ankictl) client is included in `integrations/ankictl/` and packaged as a standalone `ankictl` console command in the desktop Python wheel. Run `just bridge ping` to check its connection, or `just bridge repair --json` to list reviewer repair markers. The pinned source and license are recorded in `integrations/ankictl/SOURCE.md`.

The client currently uses the AnkiConnect API. This source inclusion does not start that API inside the fork. AnkiConnect can remain installed as a normal add-on; this fork does not bundle its third-party code. A running fork still needs AnkiConnect for `ankictl` commands until a built-in API has been implemented and verified.

No collection content, review history, profile paths, or credentials belong in this repository.

## Local verification

`just fmt`, `just lint`, and `just wheels` pass. The `aqt` wheel contains the standalone bridge source, license, and console entrypoint; the generated command reached the live AnkiConnect API. The full `just check` run reached 672 passing Rust tests, but Python tests could not load the Rust bridge on macOS 27 because the generated dylib has a misaligned `LINKEDIT` string pool. Rebuilding the bridge reproduced the loader error. This is tracked in [rust-lang/rust#157750](https://github.com/rust-lang/rust/issues/157750). Upstream's contributor lint also rejects this personal fork's commit email because it is not in `CONTRIBUTORS`; adding it there would assert a BSD license grant for upstream contributions, so it is left unchanged. The fork has not yet been launched against an isolated profile or installed over Anki.
