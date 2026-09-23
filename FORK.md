# Personal Anki fork

This fork keeps Anki's scheduler and collection format intact while adding small study tools to the desktop reviewer. The upstream project is [Ankitects Anki](https://github.com/ankitects/anki).

## Included feature

Right-click a card during review and choose **Mark for repair**. The menu records either **Bad explanation** or **Confused with another card** as a note tag containing the exact card ID. The marker syncs with the collection and does not change review scheduling. Search `tag:weibao::repair::*` in the browser to find marked notes.

The feature lives in `qt/aqt/weibao/review_capture.py` and uses Anki's reviewer hook and collection tag operation. Safe mode skips it. AnkiConnect can remain installed as a normal add-on for `ankictl`; this fork does not bundle third-party add-on code.

No collection content, review history, profile paths, or credentials belong in this repository.

## Local verification

`just fmt` and `just lint` pass. The full `just check` run reached 672 passing Rust tests, but Python tests could not load the Rust bridge on macOS 27 because the generated dylib has a misaligned `LINKEDIT` string pool. Rebuilding the bridge reproduced the loader error. This is tracked in [rust-lang/rust#157750](https://github.com/rust-lang/rust/issues/157750). The fork has not yet been launched against an isolated profile or installed over Anki.
