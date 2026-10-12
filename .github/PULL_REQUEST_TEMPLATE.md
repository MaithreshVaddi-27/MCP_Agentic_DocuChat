# Pull request template — delete what doesn't apply

## What changed and why



## How I verified

- [ ] `python -m compileall -q gradio_app.py agentic_docuchat eval`
- [ ] `python -m unittest discover -s tests -p 'test_*.py'` → OK (33 tests)
- [ ] Manual run: `python gradio_app.py` + asked a PDF question

## Docs / config

- [ ] No secrets committed (`.env`, `*.sqlite3`, PDFs)
- [ ] `README.md` / `.env.example` updated if setup or UI changed
