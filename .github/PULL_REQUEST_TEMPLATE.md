# Pull request template — delete what doesn't apply

## What changed and why



## How I verified

- [ ] `python -m py_compile gradio_app.py agentic_docuchat/app.py agentic_docuchat/rag_backend.py agentic_docuchat/persistent_memory.py agentic_docuchat/ollama_utils.py agentic_docuchat/llamacpp_utils.py agentic_docuchat/prompt_engineering.py eval/evaluate.py`
- [ ] `python -m unittest discover -s tests -p 'test_*.py'` → 9/9 OK
- [ ] Manual run: `python gradio_app.py` + asked a PDF question

## Docs / config

- [ ] No secrets committed (`.env`, `*.sqlite3`, PDFs)
- [ ] `README.md` / `.env.example` updated if setup or UI changed
