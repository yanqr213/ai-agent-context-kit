# Changelog

## 0.2.0 - 2026-06-09

- Added default `*.handoff.md` output with a copyable prompt for the next Codex, Claude Code, Cursor, or ChatGPT coding session.
- Added manifest `outputs.handoff` metadata and CLI printing for the handoff artifact.
- Added `--no-handoff` for CI jobs that only need Markdown and JSON outputs.
- Added unit and CI smoke coverage for handoff output.
- Updated the bilingual README with handoff usage and CI guidance.

## 0.1.0 - 2026-06-08

- Initial public project structure.
- Added Python standard-library CLI `aictx`.
- Added repository scanning with `.gitignore`-style ignore support.
- Added extension/path filters, size limits, character budget, and token budget estimation.
- Added Markdown bundle and JSON manifest outputs.
- Added binary, large-file, and potential-secret exclusion/warning logic.
- Added tests and GitHub Actions CI.
