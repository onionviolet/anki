# Bundled AnkiConnect source

This directory contains the AnkiConnect server from
https://github.com/FooSoft/anki-connect at commit
`4064fa142785975255457abd6a496015f5b71f38`.

Alex Yatskov's source remains under GPL-3.0-or-later. The original copyright
headers are preserved in the Python files; `LICENSE` contains the upstream
license notice. The surrounding Anki fork is AGPL-3.0-or-later.

Fork changes are limited to explicit startup after add-on loading, profile
configuration supplied by `aqt.weibao.ankiconnect`, an optional bind-port
environment override for isolated testing, graceful handling of a busy port,
and a reliable delayed callback for `guiExitAnki`. The server and API actions otherwise
use the upstream implementation.
