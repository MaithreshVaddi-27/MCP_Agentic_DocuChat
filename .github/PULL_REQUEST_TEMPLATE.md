# Pull request template — delete what doesn't apply

## What changed and why


## How I verified

- [ ] `python -m ruff check .`
- [ ] `python -m compileall -q gradio_app.py agentic_docuchat eval tests`
- [ ] `python -m unittest discover -s tests -p 'test_*.py'` → OK (101 tests)
- [ ] New behavior has a test that fails without this change
- [ ] Manual run: `python gradio_app.py` + uploaded a PDF + asked a question
- [ ] Provider touched: live-checked against the real runtime
      (`python -m agentic_docuchat.llm.models`)

## Docs / config

- [ ] No secrets committed (`.env`, `*.sqlite3`, PDFs, vectors)
- [ ] `README.md` / `.env.example` updated if setup, env vars, or UI changed
- [ ] Every new `os.getenv` has an `.env.example` entry
