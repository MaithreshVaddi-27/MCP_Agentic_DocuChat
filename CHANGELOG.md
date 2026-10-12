# Changelog

Every change worth knowing about lives here — newest first.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Changed
- Micro-architecture (v3.0.0, breaking import paths): `agentic_docuchat/rag/` (`backend.py`, `memory.py`, `prompts.py`), `agentic_docuchat/llm/` (`ollama.py`, `llamacpp.py`, `models.py`), `agentic_docuchat/mcp/` (`tools.py`, Composio loading extracted from the backend, fail-closed); `app.py` stays the UI composition root. Compile checks simplified to `python -m compileall -q gradio_app.py agentic_docuchat eval` everywhere
- Gradio 5.50 → **6.30** (migrated `Blocks(theme=…)` → `launch(theme=…)`, dropped removed `Chatbot(type=…)`), which forced the embedding stack forward: `transformers` 4.48.3 → **5.19.0**, `sentence-transformers` 5.1.2 → **6.1.0** (gradio 6 needs `huggingface-hub>=1.16`, transformers 4 caps `<1.0` — full clean-venv install proven)
- Login decoupled from sharing: real `GRADIO_USERNAME`/`GRADIO_PASSWORD` now protect the UI everywhere, and `--share`/public URLs still refuse to start without them (`_resolve_share_auth`, unit-tested)
- `.env.example`: fixed stale header comment, moved misplaced `ANSWER_LOOP_MAX_ATTEMPTS` next to `RATE_LIMIT_SECONDS`, noted the UI dropdown overrides `OLLAMA_MODEL` (all 37 vars verified read by code — none unwanted)
- `.gitignore`: covers Gradio runtime dirs (`flagged/`, `.gradio/`) and `.python-version`
- README production pass: resource requirements, full advanced-tuning table, and a Production-use checklist (auth, backups, pin-and-verify upgrades)
- Professional layout (v2.0.0): app code now lives in the `agentic_docuchat/` package (`app.py`, `rag_backend.py`, `persistent_memory.py`, `prompt_engineering.py`, `ollama_utils.py`, `llamacpp_utils.py`); `gradio_app.py` stays as a tiny launcher so `python gradio_app.py` keeps working; new `pyproject.toml` (metadata, pytest/ruff config) and `tests/__init__.py`. README, CONTRIBUTING, CI, and PR template updated for the new paths
- Project display name → `Agentic_DocuChat` (UI title/header, prompts, docstrings, README, CONTRIBUTING; repo URL and folder unchanged)
- Project name kept as `MCP_Agentic_DocuChat` — display branding reverted accordingly (package stays `agentic_docuchat`)
- Safe-minor dependency bumps (all verified on PyPI, `pip install -r requirements.txt` proven in a clean venv): `gradio 5.34.0→5.50.0`, `langchain 1.3.14→1.3.18`, `langgraph 1.2.10→1.2.14`, `langchain-google-genai 4.3.2→4.3.7`, `langchain-huggingface 1.2.2→1.2.3`, `langchain-text-splitters 1.1.2→1.1.3`, `sentence-transformers 5.1.0→5.1.2`, `transformers 4.48.0→4.48.3`, `pypdf 6.14.2→6.20.0`, `python-dotenv 1.2.2→1.2.4`, `composio(-langchain) 0.18.1→0.18.2`, `langchain-ollama 0.3.4→0.3.10`, `langchain-openai 0.3.27→1.7.0` (0.3.x caps `langchain-core<1.0` and conflicts with LangChain 1.x — must stay on 1.x), `deepeval 2.7.0→2.7.9`, `pytest 8.3.4→8.3.5`. Gradio stays on 5.x (v6 removed the `Chatbot(type=…)` API)
- README rewritten: features, quickstart with OS details, config table, structure, troubleshooting (incl. the `langchain-openai` conflict row)
- CI now tests Python 3.10–3.12 matrix (matches README's 3.10+ claim)
- Sole maintainer: git history reattributed to `Maithresh Vaddi <maithreshvaddi16@gmail.com>`; `.mailmap` added; Cline checkpoint refs removed (local rewrite — needs `push --force-with-lease` to publish)
- Default Gemini model → `gemini-3.5-flash-lite` (latest fastest/cost-efficient 3.5, per Google July 2026 release) in `.env.example`, backend default, README, and DeepEval judge

### Added
- UI model picker: the **Local model** dropdown lists models installed on your Ollama/llama.cpp servers, refreshes with status, and applies instantly with validation (`set_ollama_model` / `set_llamacpp_model`); status panel now shows the active model per provider. Verified live by switching `gemma3:1b` → `qwen3:1.7b` mid-session
- `agentic_docuchat/local_models.py` — `python -m agentic_docuchat.local_models` lists installed Ollama/llama.cpp models and prints matching `.env` lines (verified live against Ollama)
- `eval/evaluate.py` — DeepEval quality suite (faithfulness, relevancy, context precision) with offline fallback
- `AUDIT_REPORT.md` — rounds 1–2 deep-audit log
- `CONTRIBUTING.md`, `SECURITY.md`, CI workflow, PR template

### Fixed
- Upload feedback: staged progress messages ("Reading…" → "Building the search index…"), instant rejection of non-PDFs before the slow backend init, and the top "Setup needed" banner now clears on success instead of lingering (it used to render once at page load and never update)
- First-upload confirmation names the file ("Backend is ready — paper.pdf loaded.")
- Removed dead `memory_capture_instruction()` (defined, never called anywhere); ruff F-check clean, per-function usage trace confirms no other orphans
- Ollama model check is exact-match: a same-family tag (e.g. `gemma3:1b` for a `gemma3:4b` config) now yields a friendly error suggesting either `ollama pull` or the installed tag, instead of a raw server 404 (found by live manual testing)
- Eval suite gave each case its own user id — back-to-back questions tripped the per-user rate limit and scored 0s out of the box; now 4/4 with default config
- `MAX_PDF_MB` was read by the code but missing from `.env.example` — added with docs
- Singular page count ("Loaded x (1 page)"); `data/uploads/.gitkeep` is now tracked so fresh clones keep the folder
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
