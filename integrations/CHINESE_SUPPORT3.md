# Chinese Support 3 source and use

The `chinese-support-3` submodule pins [Gustaf-C/anki-chinese-support-3](https://github.com/Gustaf-C/anki-chinese-support-3). The add-on is GPL-3.0-or-later; its own `LICENSE` and file notices remain in the submodule. The fork's main Anki code remains AGPL-3.0-or-later.

The full add-on, including its local dictionary, is included in the fork's desktop wheel. On launch outside safe mode, the fork copies it into the active Anki base's `addons21/1752008591` folder if that folder is absent, then lets Anki load it normally. An existing installed copy and its configuration are preserved. No note type is enabled for field filling by this integration. It does not replace the existing `Mandarin Merged` `ToneDisplay` workflow, which preserves plain `Pinyin` and uses static tone labels.

Initialize the source with `git submodule update --init integrations/chinese-support-3` before building. Test the fork on a separate base first, using `just run -b /path/to/test-base`. The copy is intentional: Chinese Support 3 writes its configuration beside its code, and a symlink would dirty the pinned source and share settings between profiles.

The pinned upstream revision is recorded by the git submodule entry. Recheck compatibility on the fork's Anki version before using it with an existing collection. Building this branch does not install the fork over the daily Anki app.
