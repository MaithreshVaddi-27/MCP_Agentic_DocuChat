# Changelog

Every change worth knowing about lives here — newest first.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [3.2.0] - 2026-10-15

### Added
- **On-disk model discovery** (`agentic_docuchat/llm/discovery.py`), driven by each runtime's own inventory command rather than a guess at its storage layout: `ollama list`, `llama-server --cache-list`, and `mlx_lm.manage --scan`. These are authoritative — they list exactly what the runtime can load, and the last two work with no server running. `llama-server` (not the unified `llama` CLI) owns `--cache-list`. Where a command is missing or its daemon is down, discovery falls back to reading the known cache layout. Repos whose weights never finished downloading are filtered out, so nothing listed will 404 on load. Exposed as `python -m agentic_docuchat.llm.models`, which probes each runtime *and* reports what is already on disk
- Status panel and model pickers now show per-provider on-disk models and flag a configured model the runtime does not actually serve, instead of showing a green dot
- `MLX_MODEL`, `HF_HOME`, `OLLAMA_HOME`, `RATE_LIMIT_MAX_USERS`, `LLAMACPP_MODEL_DIRS` documented in `.env.example`
- 15 unit tests for discovery (`tests/test_llm_discovery.py`); 4 for SQLite connection lifecycle

### Changed
- **`DOCUMENT_PATH` removed.** PDFs are uploaded through the Gradio UI only; there is no server-side default document. `eval/evaluate.py` now takes an explicit `--document`
- Per-document Chroma collections keyed on a fingerprint of the file + embedding model, so vectors from different documents or embedding spaces never mix. Re-opening the same PDF skips re-embedding; superseded collections are swept
- Batched document embedding and one-pass ID lookup instead of a query per chunk
- SQLite connections are now a real context manager that commits, rolls back, **and closes** — sqlite3's `with connection:` ends the transaction but leaves the handle open, which leaks file descriptors in a long-running server
- Ruff configured in `pyproject.toml` on a correctness-only rule set (`E4,E7,E9,F,I,B,UP,C4`); CI now runs it, compiles `tests/`, and asserts the app boots with no document

### Fixed
- **`astream_answer` never yielded its final result.** The generator cached the finished answer and simply stopped, so anything computed after the stream never reached the UI. Found live against a reasoning model on MLX that streams ~4,000 empty chunks: the answer box sat on "…" forever. A grounding-repair rewrite was being discarded here too
- **An empty completion was silent.** Providers that answer in a non-standard `reasoning` field and leave `content` null (mlx_lm does this when a thinking model exhausts its budget) produced an answer-less turn. Both the streaming and non-streaming paths now say what happened and how to fix it, instead of showing nothing
- **A grounding repair could destroy a good answer.** The repair pass ran through the same model that had just produced a usable draft; when it came back empty, the empty string replaced the answer. Repair now keeps the original draft if the rewrite is blank
- **Uploading a PDF that is already in `data/uploads/` failed** with `shutil.SameFileError` — the directory the README tells you to keep PDFs in. Gradio passes a temp path so this never surfaced in the UI, but any script or caller passing a local path hit it. The copy is now skipped when source and destination resolve to the same file
- `llama-server` start hints no longer pass a local `*.gguf` path to `-hf`, which expects `<user>/<model>[:quant]`; local files are passed positionally and quoted, and cached repos are preferred
- `llama-server --cache-list` reports `org/repo:Q4_K_M` where the cache scan reported `org/repo`; the duplicate is collapsed in favour of the quant-tagged entry
- The app no longer crashes on a fresh clone: `RagBackend` constructs with no document and answers with an upload instruction
- Stale Chroma collections (three orphaned 95-chunk copies) are swept after a successful build; sweep failures are non-fatal
- Per-user rate-limit cooldown keys are bounded by `RATE_LIMIT_MAX_USERS` (default 1024) so a user ID cannot grow memory without limit
- Non-PDF uploads are rejected up front with a specific message

### Removed
- `AUDIT_REPORT.md` (internal process history), tracked `*.sqlite3`, `data/.gitkeep`, `data/uploads/.gitkeep`
- Unused `requests` import and dead exception handling in the backend

### Tests
- 35 → **101**, none skipped on a full-stack install; the suite builds throwaway Ollama/HF layouts in temp dirs so it never depends on which models happen to be installed

## [3.1.0] - 2026-10-13

Added the MLX provider and moved the default embeddings to `bge-large-en-v1.5`.
`agentic_docuchat/` was split into `rag/`, `llm/` and `mcp/` subpackages, and
`gradio_app.py` stayed as a thin launcher. Gradio 6 forced the embedding stack
forward to `transformers` 5 / `sentence-transformers` 6. See the release notes for
the full dependency list.

## [3.0.0]

Package layout changed. `rag_backend.py` became `agentic_docuchat/rag/backend.py`
and the Composio loader moved to `agentic_docuchat/mcp/tools.py`. Import paths that
referenced the old flat modules need updating.
