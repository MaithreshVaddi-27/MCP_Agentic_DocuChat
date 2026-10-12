# Agentic_DocuChat — Chat With Your PDFs, Privately and With Receipts

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![Gradio 5](https://img.shields.io/badge/gradio-5-orange)
![LangChain](https://img.shields.io/badge/langchain-1.3-green)
![License: MIT](https://img.shields.io/badge/license-MIT-lightgrey)

**Upload a research paper. Ask anything. Get answers that point to the exact page they came from.**

Agentic_DocuChat is a friendly, local-first reading companion. It reads your PDF,
remembers what matters to you, and answers using *your document first* — with web
search only when the paper itself doesn't have the answer. Run it fully offline with
llama.cpp or Ollama, or plug in Gemini when you want extra brainpower.

> **New here?** Get a free Gemini key → run the commands below → open the app.
> About 10 minutes total, most of it downloads.

```
You + PDF  ──▶  Agentic_DocuChat reads & indexes  ──▶  you ask  ──▶  grounded answer + page numbers
                        │                                                  │
               Chroma (local vectors)                           memory + cache (local SQLite)
```

## Contents

- [Features](#features)
- [How it works](#how-it-works)
- [Quickstart](#quickstart)
- [API keys](#api-keys)
- [Configuration](#configuration)
- [Local models](#local-models)
- [Usage](#usage)
- [Evaluation](#evaluation)
- [Project structure](#project-structure)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Security & contributing](#security--contributing)
- [License](#license)

## Features

- **Grounded answers with receipts** — every claim cites `file — page N`; a repair pass retries once if the draft looks unsupported.
- **Local-first** — PDFs, vectors, chats, and memories stay on your disk. Works fully offline with Ollama or llama.cpp.
- **Three providers** — Gemini (tool-calling agent), Ollama, and llama.cpp (both stream token-by-token).
- **Remembers you** — durable facts ("I prefer short answers") plus recent chat, stored in one local SQLite file.
- **Fast repeats** — a bounded answer cache makes identical questions instant.
- **Optional web tools** — Composio/Tavily search kicks in only when the PDF has no answer.

## How it works

1. **Upload a PDF.** Split into overlapping chunks, embedded locally, stored in Chroma.
2. **Ask.** One MMR search pulls the 4 best chunks.
3. **Answer with receipts** — the same search feeds the model and the Sources box, so they never disagree.
4. **Memory + cache** in one local SQLite file. Repeats are instant.
5. **Web search (optional)** via Composio/Tavily when the PDF has no answer.

```text
Question + selected provider
          ↓
Local answer cache (same question + same saved memories = instant reply)
          ↓
Evidence pack: your question + memories + recent chat + PDF passages
          ↓
One search pulls the 4 best chunks — used for the answer AND the Sources box
          ↓
Gemini agent (with web tools) or direct local answer, then one repair pass
          ↓
Answer + sources shown, memory updated
```

The Chroma collection name includes a fingerprint of the active document and
embedding model, so vectors from different PDFs never mix — and reopening the
app with the same PDF skips re-embedding entirely.

## Quickstart

**You need:** Python 3.10+, Git, and a Gemini API key ([get one free](https://aistudio.google.com/apikey)).

```bash
git clone https://github.com/MaithreshVaddi-27/MCP_Agentic_DocuChat.git
cd MCP_Agentic_DocuChat
python3 -m venv avenv
source avenv/bin/activate   # Windows: .\avenv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt   # first embedding download ~500 MB
cp .env.example .env        # Windows: copy .env.example .env
# paste your GEMINI_API_KEY into .env, then:
python -m unittest discover -s tests -p 'test_*.py'   # expect OK, 9 tests
python gradio_app.py
```

Open `http://127.0.0.1:7860` → **Upload a PDF** → **Process document** → ask *"What are the main findings?"*.

<details>
<summary>OS-specific notes (click to expand)</summary>

- **Windows (PowerShell):** install [Python 3.10+](https://www.python.org/downloads/) (tick **Add python.exe to PATH**) and [Git](https://git-scm.com/download/win). If activation is blocked, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`. Edit `.env` with `notepad .env`.
- **macOS:** `xcode-select --install`, then `brew install python@3.11 git`. For local models, install Ollama from [ollama.com/download](https://ollama.com/download), then `ollama pull gemma3:4b`.
- **Linux (Ubuntu/Debian):** `sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip git`. NVIDIA GPU users: afterwards install CUDA torch per [pytorch.org](https://pytorch.org/get-started/locally/).

</details>

## API keys

| Key | Needed for | Where to get it |
|-----|-----------|-----------------|
| **GEMINI_API_KEY** (recommended) | Gemini answers, online embeddings, eval judge | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) → Create API key → paste the `AIza...` value into `.env`. Free tier included. |
| **HF_TOKEN** (rarely) | HuggingFace embedding downloads if rate-limited | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) → Create new token (Read) → paste `hf_...` into `.env`. |
| **COMPOSIO_API_KEY + COMPOSIO_USER_ID** (optional) | Web search / Gmail / Calendar tools | Sign up at [composio.dev](https://composio.dev) → API keys → copy. Connect the **Tavily** toolkit (key from [tavily.com](https://tavily.com), free tier). |

Never commit `.env`. If a key leaks, revoke it where you created it.

## Configuration

Copy the template and restart the app after any change:

```bash
cp .env.example .env   # Windows: copy .env.example .env
```

| Variable | Default | What it does |
|----------|---------|--------------|
| `GEMINI_API_KEY` | — | Enables Gemini answers, online embeddings, eval judge |
| `EMBEDDING_PROVIDER` | `local` | `local` = private HuggingFace model on your machine; `online` = Google API, needs `GEMINI_API_KEY` |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Chat model for the Gemini provider |
| `OLLAMA_MODEL` / `OLLAMA_BASE_URL` | `gemma3:4b` / `http://localhost:11434` | Ollama model and server address |
| `LLAMACPP_MODEL` / `LLAMACPP_BASE_URL` | `Qwen3-4B-GGUF:Q4_0` / `http://localhost:8080/v1` | llama-server model id and address |
| `DOCUMENT_PATH` | `./data/research_paper.pdf` | PDF loaded at startup |
| `MAX_PDF_MB` | `50` | Uploads larger than this are refused politely |
| `RETRIEVAL_K` / `RETRIEVAL_FETCH_K` | `4` / `12` | MMR search depth (answer chunks / candidate pool) |
| `RATE_LIMIT_SECONDS` | `1.5` | Per-user cooldown against double-clicks |
| `GRADIO_SHARE` | `false` | Keep `false` for private docs |

The full commented list lives in [`.env.example`](.env.example) — every `os.getenv` in the code has a matching entry there.

## Local models

| Option | Install | Start | Already configured |
|--------|---------|-------|--------------------|
| Ollama (easiest) | [ollama.com/download](https://ollama.com/download) · Linux: `curl -fsSL https://ollama.com/install.sh \| sh` | `ollama pull gemma3:4b` + `ollama serve` | `OLLAMA_BASE_URL=http://localhost:11434` |
| llama.cpp (fastest) | `llama-server` from [llama.cpp releases](https://github.com/ggerganov/llama.cpp/releases) | `llama-server -hf Qwen/Qwen3-4B-GGUF:Q4_0 --port 8080` (GPU: add `-ngl 99 -c 4096`) | `LLAMACPP_BASE_URL=http://localhost:8080/v1` · check `curl http://localhost:8080/v1/models` |

Green dot = ready. Red dot = the exact command to run is in [Troubleshooting](#troubleshooting).

> Compatibility note: this release pins **Gradio 5.x**. Gradio 6 removed the `Chatbot(type=…)` API this UI uses — don't bump Gradio past 5 until the UI is migrated.

## Usage

- **Ask** about the PDF; local-model answers stream token-by-token.
- **Sources** under each answer list the `file — page N` chunks used.
- **Embeddings radio** switches local/online and rebuilds automatically.
- **Rebuild index** forces re-embedding (e.g. after changing chunk settings).
- **Clear my chat & memory** wipes your turns + saved facts for your User ID.
- **Export chat** downloads a Markdown transcript; **Copy last answer** has a clipboard fallback for non-HTTP pages.

To wipe all local memory: stop the app and delete `agentic_rag_memory.sqlite3` (chats, facts, cache, and feedback go; vectors stay).

## Evaluation

```bash
python eval/evaluate.py --document ./data/research_paper.pdf --provider llamacpp
# providers: llamacpp | ollama | gemini
```

Scores 0–1 on **faithfulness** (claims backed by the PDF?), **answer relevancy**,
and **context precision** (right pages pulled?). With `GEMINI_API_KEY` it uses the
DeepEval LLM judge; without keys it runs offline citation checks so CI stays green.
Aim for faithfulness **0.80+**. Full audit history: [`AUDIT_REPORT.md`](AUDIT_REPORT.md).

## Project structure

```text
MCP_Agentic_DocuChat/
├── gradio_app.py              # Run this (tiny launcher)
├── agentic_docuchat/          # The app itself
│   ├── app.py                 # Chat UI
│   ├── rag_backend.py         # Indexing, providers, memory, cache (single source of truth)
│   ├── persistent_memory.py   # Local SQLite (chats, facts, cache)
│   ├── prompt_engineering.py  # Evidence packs + repair loop
│   └── ollama_utils.py / llamacpp_utils.py   # Local-server health checks
├── eval/evaluate.py           # DeepEval quality suite
├── tests/                     # 9 unit tests, all passing
├── pyproject.toml / requirements.txt / .env.example
└── data/  (PDFs go in data/uploads/)
```

Ignored at runtime: `.env`, `data/uploads/`, `chroma_langchain_db/`, `*.sqlite3`, `__pycache__/`.

## Testing

```bash
python -m unittest discover -s tests -p 'test_*.py'   # Windows: "test_*.py"
python -m py_compile gradio_app.py agentic_docuchat/app.py agentic_docuchat/rag_backend.py agentic_docuchat/persistent_memory.py agentic_docuchat/ollama_utils.py agentic_docuchat/llamacpp_utils.py agentic_docuchat/prompt_engineering.py eval/evaluate.py
```

End-to-end needs a PDF + one working provider (Gemini key or local server).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `pip install` dependency conflict | Use the pinned `requirements.txt` as-is — `langchain-openai` must stay on 1.x (the 0.3.x series conflicts with LangChain 1.x). Don't mix in newer majors by hand. |
| `GEMINI_API_KEY is missing` | Paste key from [AI Studio](https://aistudio.google.com/apikey) into `.env`, restart app |
| llama.cpp 🔴 offline | `llama-server -hf Qwen/Qwen3-4B-GGUF:Q4_0 --port 8080` · verify `curl http://localhost:8080/v1/models` |
| Ollama 🔴 offline | `ollama serve` · then `ollama pull gemma3:4b` · verify `ollama list` |
| `That file doesn't look like a real PDF` | File isn't a PDF (renamed .txt/.html). Upload the original PDF |
| `PDF is 80 MB — limit is 50` | Split the PDF or raise `MAX_PDF_MB` in `.env` |
| `database is locked` | Rare now (WAL enabled). Stop other app instances, restart |
| Slow first answer | Normal — embedding model downloads once (~500 MB), then cached |
| `ModuleNotFoundError` | You forgot activation or the install failed: activate (`.\avenv\Scripts\Activate.ps1` / `source avenv/bin/activate`), reinstall requirements |

## Security & contributing

- **Security:** never commit `.env`; keep `GRADIO_SHARE=false` for private docs; PDFs, chats, and memories stay on your disk (online embeddings/Gemini send text to Google). Full policy: [`SECURITY.md`](SECURITY.md). The rate limit stops double-clicks, not attackers — don't expose the UI unauthenticated.
- **Contributing:** small, focused PRs; `agentic_docuchat/rag_backend.py` is the single source of truth; behavior changes need tests. Full guide: [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE). Educational and research use.
