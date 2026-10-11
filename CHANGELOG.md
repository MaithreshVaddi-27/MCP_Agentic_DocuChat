# Changelog

Every change worth knowing about lives here — newest first.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Changed
- Default Gemini model → `gemini-3.5-flash-lite` (latest fastest/cost-efficient 3.5, per Google July 2026 release) in `.env.example`, backend default, README, and DeepEval judge

### Added
- `eval/evaluate.py` — DeepEval quality suite (faithfulness, relevancy, context precision) with offline fallback
- `AUDIT_REPORT.md` — rounds 1–2 deep-audit log
- `CONTRIBUTING.md`, `SECURITY.md`, CI workflow, PR template

### Fixed
- Windows SQLite teardown crash — WAL + `busy_timeout=30s`, `NamedTemporaryFile` tests (9/9 pass)
- `database is locked` on concurrent asks — same WAL pragmas
- `transformers==5.14.1` (nonexistent) → `4.48.0`; all deps pinned
- Fake-PDF crash → suffix + `%PDF-` magic-bytes + `MAX_PDF_MB` checks
- Copy-button clipboard fallback; theme toggle persists via `localStorage`

### Removed
- `main.py` / `legacy_cli.py` — deleted divergent duplicate CLI; `rag_backend.py` is the single source of truth
- Stale `main.py` references, duplicate README Testing/Troubleshooting/Security/License sections

### Polish (final pass)
- Fixed broken `ci.yml` (was wrapped in a markdown code fence — now real YAML)
- Fixed `GEMINI_MODEL=gemini-3.1-flash-lite` (nonexistent) → `gemini-2.5-flash` in `.env.example`
- Repaired `AUDIT_REPORT.md` (round-2 edit had spliced a stray line into the round-1 log)
- Added `data/uploads/.gitkeep` so the ignored uploads folder survives fresh clones
- Humanized every module docstring (`rag_backend`, `persistent_memory`, `gradio_app`, `prompt_engineering`, `ollama_utils`, `llamacpp_utils`, `eval/evaluate.py`)
- Condensed README contributor section from ~20 jargon bullets to one friendly paragraph
