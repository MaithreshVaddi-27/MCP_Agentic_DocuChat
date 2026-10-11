# Pull request template — delete what doesn't apply

## What changed and why



## How I verified

- [ ] `python -m py_compile rag_backend.py gradio_app.py persistent_memory.py ollama_utils.py llamacpp_utils.py prompt_engineering.py eval/evaluate.py`
- [ ] `python -m unittest discover -s tests -p 'test_*.py'` → 9/9 OK
- [ ] Manual run: `python gradio_app.py` + asked a PDF question

## Docs / config

- [ ] No secrets committed (`.env`, `*.sqlite3`, PDFs)
- [ ] `README.md` / `.env.example` updated if setup or UI changed
