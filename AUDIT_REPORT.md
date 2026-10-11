# Deep Audit — Agentic_DocuChat

Date: 2026-10-11 · Round 3 (safe-minor upgrades, rename, single-maintainer) · Skills: code-review, dependency-audit, security-review
Repo: `MaithreshVaddi-27/MCP_Agentic_DocuChat` (URL unchanged), branch `main`

## Round-3 verdict: 8.7/10 — current, renamed, single-maintainer

Round 2 scored 8.4/10. Since then: 16 pins bumped within safe series
(verified each on PyPI), display name → `Agentic_DocuChat`, Gradio
inline-`State` fix, CI Python matrix 3.10–3.12, history reattributed to
sole maintainer + `.mailmap` (local only, not pushed).

## What changed in round 3

Round 1 scored 7.2/10. Since then: Windows SQLite crash fixed (9/9 tests),
deps pinned, PDF validation added, `main.py`/`legacy_cli.py` duplication
deleted, copy-button + theme-toggle JS hardened, eval suite added.

## What changed in round 2

| Area | Action |
|------|--------|
| Bloat removed | `legacy_cli.py` (314-line dead duplicate) deleted; all `__pycache__/` + `*.pyc` purged; stale `main.py` references scrubbed from README (7 spots); duplicate Testing/Troubleshooting sections merged into one |
| `.env.example` | Fixed stale "original main.py flow expects these values" comment |
| `gradio_app.py` | `COPY_JS` clipboard fallback for non-HTTPS (`execCommand` path); `THEME_TOGGLE_JS` toggles `documentElement` + persists to `localStorage` |
| `eval/evaluate.py` | Removed phantom `--judge-model` flag mention (never implemented) |
| `rag_backend.py` | Docstring decoupled from deleted CLI ("for the CLI and Gradio" → standalone) |
| README | Full rewrite: OS-separated setup (Windows/macOS/Linux), API-key table with click paths, single Troubleshooting table, single Testing block, contributor backend section kept |

## Remaining findings (by severity)

### Medium
1. **`composio==0.18.1` stale + no live CVE check.** Offline manifest review is clean (all MIT/Apache), but run `pip install pip-audit && pip-audit -r requirements.txt` before any public deploy.
2. **No auth by default on LAN.** `auth=None` unless `GRADIO_SHARE=true`. Bind `127.0.0.1` or add login for shared machines.
3. **`RagBackend` God class (730+ lines, ~15 methods).** Works, but next refactor should split `indexing.py` / `providers.py` / `agent.py`.

### Low
4. No `Dockerfile` / CI workflow / linter config. Suggested, not scaffolded (deploy target unknown).
5. `torch` (~2 GB via sentence-transformers) download size only mentioned in passing — fine for README, add to release notes.
6. Rate limit is per-process memory — noted in README as anti-double-click, not security.

## Dependency audit (round 2)

All 20 pins in `requirements.txt` resolve to real releases.
`transformers==4.48.0` + `sentence-transformers==5.1.0` are a compatible pair.
`gradio==5.34.0`, `langchain*==1.3/0.4` consistent. `deepeval==2.7.0` + `pytest==8.3.4`
isolated under an eval comment. Licenses: permissive throughout, no GPL.

## Verification (round 2)

```
python -m py_compile <all 7 modules>   # OK
python -m unittest discover -s tests   # 9/9 OK
secret scan (api_key|password|secret|token)  # env-reads only, no hardcoded values
```

## Round-1 log (kept for history)

| # | Bug | Severity | Status |
|---|-----|----------|--------|
| 1 | SQLite tests fail on Windows (`PermissionError WinError 32`) | High | **Fixed** — WAL + `busy_timeout=30s`, `NamedTemporaryFile` tests → **9/9 pass** |
| 2 | `database is locked` on concurrent asks | High | **Fixed** — same WAL pragmas |
| 3 | `transformers==5.14.1` nonexistent | High | **Fixed** — `4.48.0` |
| 4 | Floating pins (`gradio>=5.0,<6.0`…) | Medium | **Fixed** — all pinned |
| 5 | Fake-PDF crash | Medium | **Fixed** — suffix + magic-bytes + size cap |
| 6 | `import json` in function body | Low | **Fixed** |
| 7 | `mkdir(".")` no-op | Low | **Fixed** |
| 8 | `main.py` duplicated backend | Medium | **Fixed** — deleted in round 2 |

---

## Round-1 detail (original auditor notes, Commit `0c2679f` on `main`)

### Scope

Read every Python file end-to-end (1,744 lines), ran `py_compile` (pass),
`unittest discover` (9 tests), and a secret scan (no hardcoded keys).

## Bugs found and fixed

| # | Bug | Severity | Status |
|---|-----|----------|--------|
| 1 | SQLite tests fail on Windows — `TemporaryDirectory` deleted while `-journal`/`-wal` handle still open (`PermissionError WinError 32`) | High | **Fixed** — WAL + `busy_timeout=30s` pragmas, `check_same_thread=False`, `close()` checkpoint helper, tests use `NamedTemporaryFile(delete=False)` + sidecar cleanup. Result: **9/9 pass** |
| 2 | Concurrent Gradio clicks → `database is locked` (default 5 s SQLite timeout, no WAL) | High | **Fixed** — same pragmas as above |
| 3 | `transformers==5.14.1` does not exist publicly — fresh `pip install` breaks | High | **Fixed** — pinned `transformers==4.48.0`, `sentence-transformers==5.1.0` |
| 4 | Floating pins `gradio>=5.0,<6.0`, `langchain-ollama>=0.3.0,<1.0`, `langchain-openai>=0.3.0,<1.0` — LangChain 1.x breaks weekly | Medium | **Fixed** — all pinned (`gradio==5.34.0`, `langchain-ollama==0.3.4`, `langchain-openai==0.3.27`) |
| 5 | Any extension accepted as PDF server-side; renamed `.txt` crashes inside pypdf | Medium | **Fixed** — `.pdf` suffix + `%PDF-` magic-bytes + `MAX_PDF_MB=50` checks with friendly messages in `_load_documents()` |
| 6 | `import json` buried inside `ollama_status()` function body | Low | **Fixed** — moved to top-level imports |
| 7 | `PersistentMemory.__init__` calls `mkdir` on `"."` parent harmlessly | Low | **Fixed** — guard `if parent not in ("", ".")` |
| 8 | `main.py` duplicates backend logic (chunking 800/150 vs 700/100, hard `raise` on keys) — fixes in one never reach the other | Medium | **Fixed (bloat removal)** — copied to `legacy_cli.py` with a "reference only" header; new code should treat `rag_backend.py` as the single source of truth |

## Open issues (not fixed — need your decision)

| # | Issue | Why left open |
|---|-------|---------------|
| 9 | No auth on local UI by default (`auth=None` unless sharing) — anyone on LAN can read PDFs + memory | Needs product call: bind `127.0.0.1` vs add login. One-line change in `gradio_app._launch()` |
| 10 | Rate limit is in-memory per process — bypassed by restart or changing the User ID box | Acceptable for a demo; a real fix needs Redis/DB-backed limits |
| 11 | `composio==0.18.1` is stale; `torch` (~2 GB via sentence-transformers) undocumented | Run `pip-audit` live; document the download size in setup |
| 12 | No Dockerfile / CI / linter | Suggested `Dockerfile` + GitHub Action in README; not scaffolded to avoid guessing your deploy target |

## Optimizations already in the code (kept)

- Single MMR retrieval per question, reused for generation + agent tool + UI sources
- Embedding/model/agent objects cached per config, not rebuilt per call
- Stable content-hash Chroma IDs + collection fingerprint → restart skips re-embedding
- Short-TTL health probes (15 s) instead of `nvidia-smi` + HTTP on every message
- Cache key on durable memory only (not recent turns) → repeats actually hit
- Structured `logging` with `LOG_LEVEL`, retry-with-backoff on local-model hiccups

## Optimizations applied in this pass

1. SQLite WAL + NORMAL sync — concurrent reads no longer block writes
2. `busy_timeout=30 s` — slow embedding writes ride out instead of erroring
3. Magic-bytes pre-check avoids a wasted full PDF parse on wrong files
4. Pinned deps — reproducible installs, no surprise major bumps
5. `legacy_cli.py` header — stops future divergence at the source

## Further optimization ideas (roadmap)

- Batch `store.add_documents` in chunks of 100 for very large PDFs (lower peak RAM)
- Add `retrieval_score_threshold` to drop weak MMR hits before they pollute context
- Stream Gemini too (currently only Ollama/llama.cpp stream) via `model.astream`
- Cache embedding vectors per chunk-hash on disk to survive collection wipes
- Add `pytest -n auto` + `pytest-benchmark` for retrieval latency regression gates

## Verification

```
python -m unittest discover -s tests -p "test_*.py"   # 9/9 OK
python -m py_compile <all 7 py files>                  # OK
secret scan (api_key|password|secret|token)            # only .env reads, no hardcoded values
```

## Skills used

- `code-review` + `code-reviewer` — structure, duplication, naming, thresholds (God class `RagBackend` 716 lines noted, split deferred)
- `dependency-auditor` — offline manifest review (no live CVE feed; pair with `pip-audit`)
- `secure-workflow-guide` — adapted from smart-contract flow; Slither steps N/A for Python, manual review applied instead (prompt-injection guardrails, upload validation, auth gaps noted above)
