# MCP_Agentic_DocuChat

**Upload a PDF. Ask anything. Get answers that point to the exact page they came from.**

A local-first reading companion. Your documents, vectors, chats, and memories stay on
your disk. Runs fully offline against Ollama, llama.cpp, or MLX — Gemini is optional.

```text
   PDF  ──▶  chunk + embed (local)  ──▶  Chroma  ──▶  question  ──▶  answer + page citations
                                                    │                    ▲
                                        SQLite: memory + answer cache ─┘
```

## Contents

- [Quickstart](#quickstart)
- [Local models](#local-models)
- [How it works](#how-it-works)
- [Configuration](#configuration)
- [Using the app](#using-the-app)
- [Project layout](#project-layout)
- [Evaluation](#evaluation)
- [Testing](#testing)
- [Production use](#production-use)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Quickstart

**Requires** Python 3.10+, ~4 GB free disk, and a local model runtime (or a free
[Gemini key](https://aistudio.google.com/apikey)).

```bash
git clone https://github.com/MaithreshVaddi-27/MCP_Agentic_DocuChat.git
cd MCP_Agentic_DocuChat

python3 -m venv avenv
source avenv/bin/activate            # Windows: .\avenv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

cp .env.example .env                 # optional — defaults run fine
python gradio_app.py
```

Open <http://127.0.0.1:7860>, drop in a PDF, press **Process document**, and ask
*"What are the main findings?"*.

The first run downloads the embedding model once (~1.3 GB, a few minutes). After
that, restarts are fast and re-opening the same PDF skips re-embedding entirely.

<details>
<summary>Platform notes</summary>

- **macOS** — `xcode-select --install`, then `brew install python@3.11 git`.
  For local models: `brew install ollama llama.cpp` and `pipx install mlx-lm`.
- **Linux** — `sudo apt update && sudo apt install -y python3.11 python3.11-venv git`.
  NVIDIA users: install CUDA torch per [pytorch.org](https://pytorch.org/get-started/locally/).
- **Windows** — install [Python 3.10+](https://www.python.org/downloads/) with
  **Add python.exe to PATH**. If activation is blocked:
  `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`.

</details>

---

## Local models

MCP_Agentic_DocuChat talks to three OpenAI-compatible local runtimes. Start the one
you want; the app finds it, lists the models it serves, and lets you switch between
them in the UI.

| Runtime | Install | Start | Default URL |
|---------|---------|-------|-------------|
| **Ollama** | [ollama.com/download](https://ollama.com/download) | `ollama serve` | `http://localhost:11434` |
| **llama.cpp** | `brew install llama.cpp`, or [releases](https://github.com/ggml-org/llama.cpp/releases) | `llama-server -hf <repo> --port 8080` | `http://localhost:8080/v1` |
| **MLX** (Apple Silicon) | `pipx install mlx-lm` | `mlx_lm.server --model <repo> --port 8081` | `http://localhost:8081/v1` |
| **Gemini** (optional) | — | API key in `.env` | managed |

### Finding what you already have

```bash
python -m agentic_docuchat.llm.models
```

This is the fastest way to answer *"which model should I point this at?"*. It probes
each runtime **and** scans disk, so it still tells you what you have when nothing is
running yet:

```text
ollama (http://localhost:11434): offline — 2 model(s) already on disk: gemma3:1b, qwen3:1.7b
llamacpp (http://localhost:8080/v1): offline — 3 model(s) already on disk: ggml-org/SmolLM3-3B-GGUF, ...
mlx (http://localhost:8081/v1): offline — 7 model(s) already on disk: mlx-community/gemma-3-4b-it-4bit, ...

No provider is serving right now. Start one:
  ollama    -> ollama serve
  llamacpp  -> llama-server -hf ggml-org/SmolLM3-3B-GGUF --port 8080
  mlx       -> mlx_lm.server --model mlx-community/gemma-3-4b-it-4bit --port 8081
```

Discovery asks each runtime to inventory itself, so it reports exactly what that
runtime can actually load:

| Runtime | Command used |
|---------|--------------|
| Ollama | `ollama list` |
| llama.cpp | `llama-server --cache-list` |
| MLX | `mlx_lm.manage --scan` |

The last two work with nothing running, so the list is still useful on a stopped
machine. When a command is missing (or Ollama's daemon is down) discovery falls back
to reading the known cache layout — the Hugging Face hub plus any extra directories in
`LLAMACPP_MODEL_DIRS`. Repos whose weights never finished downloading are filtered
out, so nothing listed here will 404 on load. The same information appears in the app's
status panel.

---

## How it works

1. **Upload a PDF.** Pages are split into overlapping chunks, embedded locally, and
   stored in Chroma. Uploads are validated by extension, `%PDF-` header, and size cap.
2. **Ask.** One MMR search pulls the best `RETRIEVAL_K` chunks. That single search
   feeds both the model and the Sources box, so they can never disagree.
3. **Answer with receipts.** The model answers from an explicitly labelled evidence
   pack. Retrieved text is treated as evidence, never as instructions — a PDF
   containing *"ignore your rules"* does not get to give them.
4. **Grounding repair.** If a draft cites no page and does not admit a gap, it gets
   one rewrite pass before being shown.
5. **Memory and cache** live in one local SQLite file. Durable facts are captured
   automatically ("I prefer short answers"); repeat questions are instant.

Each document gets its own Chroma collection, keyed on a fingerprint of the file and
the active embedding model — so vectors from different documents or embedding spaces
never mix, re-opening the same PDF is free, and superseded collections are swept
automatically rather than accumulating.

---

## Configuration

Every setting lives in `.env` (copy from `.env.example`); restart the app after
changing one. Documents are *not* configured here — PDFs are uploaded through the UI.

### Frequently changed

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_MODEL` / `OLLAMA_BASE_URL` | `gemma3:4b` / `http://localhost:11434` | Ollama runtime |
| `LLAMACPP_MODEL` / `LLAMACPP_BASE_URL` | `Qwen3-4B-GGUF:Q4_0` / `http://localhost:8080/v1` | llama.cpp runtime |
| `MLX_MODEL` / `MLX_BASE_URL` | `mlx-community/gemma-3-4b-it-4bit` / `http://localhost:8081/v1` | MLX runtime |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | — / `gemini-3.5-flash-lite` | Gemini provider |
| `EMBEDDING_PROVIDER` | `local` | `local` = private HuggingFace model; `online` = Google API (needs `GEMINI_API_KEY`) |
| `RETRIEVAL_K` / `RETRIEVAL_FETCH_K` | `4` / `12` | MMR search depth (chunks sent / candidate pool) |
| `MAX_PDF_MB` | `50` | Upload size cap |
| `GRADIO_USERNAME` / `GRADIO_PASSWORD` | placeholders (login off) | Require login everywhere |
| `GRADIO_SHARE` | `false` | `true` = temporary public URL (refuses to start without login) |

### Everything else

`requirements.txt` aside, the full commented list — 44 variables covering provider
timeouts, chunking, cache bounds, storage paths, rate limiting, and logging — lives in
[`.env.example`](.env.example). Every `os.getenv` in the code has a matching entry
there; CI and the audit check below keep it that way.

```bash
# verify no undocumented env var crept in
diff <(grep -rhoE 'os\.getenv\("[A-Z0-9_]+"' agentic_docuchat eval | sed 's/os.getenv("//;s/"//' | sort -u) \
     <(grep -oE '^[A-Z0-9_]+=' .env.example | sed 's/=//' | sort -u)
```

---

## Using the app

| Control | What it does |
|---------|--------------|
| **Provider** | Gemini, llama.cpp, Ollama, or MLX. |
| **Local model** | Lists what the chosen runtime actually serves. Switching applies instantly and is validated — a typo gets a helpful error, not a stack trace. |
| **Embeddings** | Switch local/online; the index rebuilds automatically because vectors from different models are not comparable. |
| **Sources** | Lists the `file — page N` chunks behind each answer. |
| **Upload a PDF** / **Rebuild index** | Load a document, or force re-embedding after changing chunk settings. |
| **Clear my chat & memory** | Wipes your turns and saved facts for the current User ID. |
| **Export chat** / **Copy last answer** | Download a transcript, or copy to clipboard. |

Status dots are honest: a green dot next to a model the runtime doesn't actually serve
is flagged before you hit a 404.

To wipe everything local: stop the app and delete `agentic_rag_memory.sqlite3` (chats,
facts, cache, feedback) and `chroma_langchain_db/` (vectors).

---

## Project layout

```text
MCP_Agentic_DocuChat/
├── gradio_app.py                 # launcher — python gradio_app.py
├── agentic_docuchat/
│   ├── app.py                    # Gradio UI (composition root)
│   ├── rag/
│   │   ├── backend.py            # indexing, providers, retrieval, agent (single source of truth)
│   │   ├── memory.py             # local SQLite: chats, facts, answer cache
│   │   └── prompts.py            # evidence packs + grounding repair
│   ├── llm/
│   │   ├── discovery.py          # on-disk model discovery for Ollama / llama.cpp / MLX
│   │   ├── ollama.py             # per-provider health probes (+ what is on disk)
│   │   ├── llamacpp.py
│   │   ├── mlx.py
│   │   └── models.py             # python -m agentic_docuchat.llm.models
│   └── mcp/
│       └── tools.py              # Composio loader (fail-closed, lazy)
├── eval/evaluate.py              # DeepEval quality suite
├── tests/                        # 101 unit tests
└── pyproject.toml · requirements.txt · .env.example
```

Runtime artifacts are git-ignored: `.env`, `data/uploads/`, `chroma_langchain_db/`,
`*.sqlite3`, `__pycache__/`.

---

## Evaluation

```bash
python eval/evaluate.py --document ./data/uploads/your.pdf --provider llamacpp
# providers: llamacpp | ollama | mlx | gemini
```

Scores 0–1 on **faithfulness** (claims backed by the document), **answer relevancy**,
and **context precision** (right pages pulled), across four fixed questions — one of
which no document can answer, to check the model says so honestly. With
`GEMINI_API_KEY` set, DeepEval's LLM judge does the scoring; without keys it falls back
to offline citation checks so CI stays green anywhere. Aim for faithfulness **0.80+**.

---

## Testing

```bash
python -m ruff check .                              # lint gate (pyproject-configured)
python -m compileall -q gradio_app.py agentic_docuchat eval tests
python -m unittest discover -s tests -p 'test_*.py'  # 101 tests
```

The suite is self-contained: it builds throwaway Ollama/Hugging Face layouts in temp
directories, so nothing depends on which models happen to be installed on the machine
running it. Tests that need the full LangChain stack skip themselves cleanly in a light
environment. End-to-end runs need a PDF and one working provider.

CI runs this on Python 3.10–3.12, plus a boot smoke test that asserts the app starts
with no document (a fresh clone has none) and a wheel build/install check.

---

## Production use

Beyond your own laptop:

- **Lock the UI down.** `GRADIO_SHARE=false` by default. Set `GRADIO_USERNAME` /
  `GRADIO_PASSWORD` and login applies everywhere; public sharing without credentials is
  refused at startup. Never expose an unauthenticated Gradio port to an untrusted
  network — prefer an SSH tunnel or an authenticated reverse proxy. The per-user rate
  limit stops double-clicks, not attackers.
- **Know what to back up.** `agentic_rag_memory.sqlite3` (chats, facts, cache),
  `data/uploads/` (your PDFs), `chroma_langchain_db/` (vectors). Everything else rebuilds.
- **Pin and verify before upgrading.** Dependencies are pinned in `requirements.txt`.
  `langchain-openai` must stay on 1.x — 0.3.x caps `langchain-core<1.0` and conflicts
  with the LangChain 1.x family. After any bump, run the [Testing](#testing) commands
  and ask one real question against a real PDF.
- **Watch the first run.** The embedding model downloads once (~1.3 GB). The UI narrates
  each stage so a slow first upload is visibly progress rather than a hang.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| 🔴 Ollama offline | `ollama serve`, then `ollama pull gemma3:4b`. `python -m agentic_docuchat.llm.models` shows what you already have. |
| 🔴 llama.cpp offline | `llama-server -hf ggml-org/SmolLM3-3B-GGUF --port 8080`. Verify with `curl http://localhost:8080/v1/models`. |
| 🔴 MLX offline | `mlx_lm.server --model mlx-community/gemma-3-4b-it-4bit --port 8081`. Verify with `curl http://localhost:8081/v1/models`. |
| `not installed — pick one below` | The configured model isn't on that server. Pick a real one from the **Local model** dropdown. |
| `No document loaded` | Expected on a fresh clone. Upload a PDF and press **Process document**. |
| `That file doesn't look like a real PDF` | Renamed `.txt`/`.html`. Upload the original PDF. |
| `PDF is 80 MB — limit is 50` | Split the file, or raise `MAX_PDF_MB`. |
| `GEMINI_API_KEY is missing` | Add a key from [AI Studio](https://aistudio.google.com/apikey) to `.env`. |
| Answer box shows `…` and never finishes | The provider is streaming empty chunks. Check the provider log; a reasoning/thinking model that exhausts its token budget answers in a non-standard field. Pick a non-thinking model, or raise the server's budget (`--max-tokens` for `mlx_lm.server`). |
| "The model returned an empty answer" | Same cause, reported instead of hanging. Raise the server's token budget or choose a model without a thinking mode. |
| `database is locked` | Rare (WAL is on). Close other instances and restart. |
| Slow first answer | Normal — the embedding model is downloading once (~1.3 GB), then cached. |
| `pip install` conflict | Use `requirements.txt` as pinned; see [Production use](#production-use). |
| `ModuleNotFoundError` | You forgot to activate the venv, or the install failed. Re-activate and reinstall. |

---

## Contributing

Small, focused PRs; behavior changes need a test that fails before and passes after.
Full guide in [`CONTRIBUTING.md`](CONTRIBUTING.md).

**Security** — never commit `.env`; keep sharing off for private documents; PDFs, chats,
and memories stay on your disk unless you enable online embeddings or Gemini. Report
vulnerabilities privately, not as a public issue: [`SECURITY.md`](SECURITY.md).

## License

MIT — see [`LICENSE`](LICENSE). Educational and research use.