# Contributing to MCP_Agentic_DocuChat

Thanks for stopping by — small, focused pull requests beat big ones, and
there's no such thing as a silly question in a review.

## Setup

```bash
git clone https://github.com/MaithreshVaddi-27/MCP_Agentic_DocuChat.git
cd MCP_Agentic_DocuChat
python3 -m venv avenv
source avenv/bin/activate   # Windows: .\avenv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
```

## Before you push

```bash
python -m compileall -q gradio_app.py agentic_docuchat eval
python -m unittest discover -s tests -p 'test_*.py'   # must be OK — 33 tests (22 skip without the full stack)
```

## Rules

1. **Never commit secrets.** `.env`, `*.sqlite3`, `data/uploads/`, `chroma_langchain_db/` are git-ignored. If a key leaks, revoke it where it was created and tell the maintainer.
2. **One concern per PR.** Don't mix a bug fix with a refactor.
3. **`agentic_docuchat/rag/backend.py` is the single source of truth.** Don't reintroduce a parallel CLI/agent flow — extend the backend and wire it through `agentic_docuchat/app.py` (launched via `gradio_app.py`).
4. **Keep it local-first.** New features must work with no API keys (offline fallback) unless they are explicitly cloud features.
5. **Tests for behavior changes.** Bug fix? Add or update a test in `tests/` that fails before and passes after.
6. **Human tone.** User-facing strings (errors, status, README) should read like a helpful friend, not a stack trace.
7. **Update docs.** If you change setup, env vars, or the UI, update `README.md` and `.env.example` in the same PR.
