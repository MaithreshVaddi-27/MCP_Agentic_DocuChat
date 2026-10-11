# Agentic_DocuChat — Chat With Your PDFs, Privately and With Receipts

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![Gradio 5](https://img.shields.io/badge/gradio-5-orange)
![LangChain](https://img.shields.io/badge/langchain-1.3-green)
![License: MIT](https://img.shields.io/badge/license-MIT-lightgrey)

**Upload a research paper. Ask anything. Get answers that point to the exact page they came from.**

Agentic_DocuChat is a friendly, local-first reading companion. It reads your PDF, remembers
what matters to you, and answers using *your document first* — with web search only
when the paper itself doesn't have the answer. Run it fully offline with llama.cpp
or Ollama, or plug in Gemini when you want extra brainpower.

> **New here?** Pick your OS below → get the free Gemini key → run one command.
> About 10 minutes total, most of it downloads.

```
You + PDF  ──▶  Agentic_DocuChat reads & indexes  ──▶  you ask  ──▶  grounded answer + page numbers
                        │                                           │
              Chroma (local vectors)                    memory + cache (local SQLite)
```

## Contents

- [How it works](#how-it-works)
- [Get your API keys](#get-your-api-keys)
- [Setup on Windows](#setup-on-windows-powershell)
- [Setup on macOS](#setup-on-macos-terminal)
- [Setup on Linux](#setup-on-linux-ubuntudebian)
- [Run the app](#run-the-app)
- [Local models](#local-models-ollama-and-llamacpp)
- [Configure (.env reference)](#configure-env-reference)
- [Use it](#use-it)
- [Evaluation](#is-it-any-good-evaluation)
- [Project layout](#project-layout)
- [Troubleshooting](#troubleshooting)
- [Testing](#testing)
- [Security](#security)
- [License](#license)

## How it works

1. **Upload a PDF.** Split into overlapping chunks, embedded locally, stored in Chroma.
2. **Ask.** One MMR search pulls the 4 best chunks.
3. **Answer with receipts** — `filename — page N`. A repair loop retries once if
   the draft looks unsupported.
4. **Memory + cache** in one local SQLite file. Repeats are instant.
5. **Web search (optional)** via Composio/Tavily when the PDF has no answer.

## Get your API keys

| Key | Needed for | Where to get it (step by step) |
|-----|-----------|--------------------------------|
| **GEMINI_API_KEY** (recommended) | Gemini answers, online embeddings, eval judge | 1. Open [aistudio.google.com/apikey](https://aistudio.google.com/apikey), sign in. 2. **Create API key → Create API key in new project**. 3. Copy the `AIza...` value into `.env`. Free tier included. |
| **HF_TOKEN** (rarely) | HuggingFace embedding downloads if rate-limited | 1. Open [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens). 2. **Create new token → Read**. 3. Copy `hf_...` into `.env`. |
| **COMPOSIO_API_KEY + COMPOSIO_USER_ID** (optional) | Web search / Gmail / Calendar tools | 1. Sign up at [composio.dev](https://composio.dev). 2. Dashboard → API keys → copy. 3. Connect the **Tavily** toolkit (key from [tavily.com](https://tavily.com), free tier) and copy your entity/user ID. |

Never commit `.env`. Revoke a leaked key where you created it.

## Setup on Windows (PowerShell)

> Needs: [Python 3.10+](https://www.python.org/downloads/) (tick **Add python.exe to PATH**), [Git](https://git-scm.com/download/win).

```powershell
git clone https://github.com/MaithreshVaddi-27/MCP_Agentic_DocuChat.git
cd MCP_Agentic_DocuChat
py -m venv avenv
.\avenv\Scripts\Activate.ps1
# Blocked? Run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
copy .env.example .env
notepad .env   # paste GEMINI_API_KEY, save, close
python -m unittest discover -s tests -p "test_*.py"   # expect OK, 9 tests
python gradio_app.py
```

## Setup on macOS (Terminal)

> Needs: Xcode tools `xcode-select --install`, [Homebrew](https://brew.sh), then `brew install python@3.11 git`.

```bash
git clone https://github.com/MaithreshVaddi-27/MCP_Agentic_DocuChat.git
cd MCP_Agentic_DocuChat
python3 -m venv avenv
source avenv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt   # first embedding download ~500 MB
cp .env.example .env
nano .env   # paste GEMINI_API_KEY, Ctrl+O Enter, Ctrl+X
python -m unittest discover -s tests -p 'test_*.py'
python gradio_app.py
```

> Apple Silicon: install Ollama from [ollama.com/download](https://ollama.com/download), then `ollama pull gemma3:4b`.

## Setup on Linux (Ubuntu/Debian)

```bash
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip git
git clone https://github.com/MaithreshVaddi-27/MCP_Agentic_DocuChat.git
cd MCP_Agentic_DocuChat
python3 -m venv avenv
source avenv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
# NVIDIA GPU: afterwards install CUDA torch per https://pytorch.org/get-started/locally/
cp .env.example .env
nano .env   # paste GEMINI_API_KEY
python -m unittest discover -s tests -p 'test_*.py'
python gradio_app.py
```

## Run the app

```bash
# every new terminal, activate first:
# Windows: .\avenv\Scripts\Activate.ps1 | Mac/Linux: source avenv/bin/activate
python gradio_app.py
```

Open `http://127.0.0.1:7860` → **Upload a PDF** → **Process document** → ask *"What are the main findings?"*.

## Local models (Ollama and llama.cpp)

| Option | Install | Start | Already configured |
|--------|---------|-------|--------------------|
| Ollama (easiest) | [ollama.com/download](https://ollama.com/download) · Linux: `curl -fsSL https://ollama.com/install.sh \| sh` | `ollama pull gemma3:4b` + `ollama serve` | `OLLAMA_BASE_URL=http://localhost:11434` |
| llama.cpp (fastest) | `llama-server` from [llama.cpp releases](https://github.com/ggerganov/llama.cpp/releases) | `llama-server -hf Qwen/Qwen3-4B-GGUF:Q4_0 --port 8080` (GPU: add `-ngl 99 -c 4096`) | `LLAMACPP_BASE_URL=http://localhost:8080/v1` · check `curl http://localhost:8080/v1/models` |

Green dot = ready. Red dot = the exact command to run is in Troubleshooting.

## Configure (.env reference)

```bash
cp .env.example .env   # Windows: copy .env.example .env
```

```env
GEMINI_API_KEY=AIza...            # from AI Studio (recommended)
EMBEDDING_PROVIDER=local          # local = private; online = Google API
GEMINI_MODEL=gemini-3.5-flash-lite
OLLAMA_MODEL=gemma3:4b
LLAMACPP_MODEL=Qwen3-4B-GGUF:Q4_0
COMPOSIO_API_KEY=...              # only for web search/tools
COMPOSIO_USER_ID=...
COMPOSIO_TOOLKITS=TAVILY
```

Full list with comments: `.env.example`. Restart the app after editing `.env`.

## Use it

- **Ask** about the PDF; answers stream token-by-token for local models.
- **Sources** under each answer list `file — page N` chunks used.
- **Embeddings radio** switches local/online and rebuilds automatically.
- **Rebuild index** forces re-embedding (e.g. after changing chunk settings).
- **Clear my chat & memory** wipes your turns + saved facts for your User ID.
- **Export chat** downloads a Markdown transcript. **Copy last answer** uses a
  clipboard fallback for non-HTTPS pages.

## Is it any good? (evaluation)

```bash
python eval/evaluate.py --document ./data/research_paper.pdf --provider llamacpp
# providers: llamacpp | ollama | gemini
```

Scores 0–1 on **faithfulness** (claims backed by the PDF?), **answer relevancy**,
and **context precision** (right pages pulled?). With `GEMINI_API_KEY` it uses the
DeepEval LLM judge; without keys it runs offline citation checks so CI stays green.
Aim for faithfulness **0.80+**. Full audit: `AUDIT_REPORT.md`.

## Project layout

```text
MCP_Agentic_DocuChat/
├── gradio_app.py              # Run this (tiny launcher)
├── agentic_docuchat/          # The app itself
│   ├── app.py                 # Chat UI
│   ├── rag_backend.py         # Indexing, providers, memory, cache
│   ├── persistent_memory.py   # Local SQLite (chats, facts, cache)
│   ├── prompt_engineering.py  # Evidence packs + repair loop
│   └── ollama_utils.py / llamacpp_utils.py
├── eval/evaluate.py           # DeepEval quality suite
├── tests/                     # 9 unit tests, all passing
├── pyproject.toml / requirements.txt / .env.example
└── data/  (PDFs go in data/uploads/)
```

Ignored at runtime: `.env`, `data/uploads/`, `chroma_langchain_db/`, `*.sqlite3`, `__pycache__/`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `GEMINI_API_KEY is missing` | Paste key from [AI Studio](https://aistudio.google.com/apikey) into `.env`, restart app |
| llama.cpp 🔴 offline | `llama-server -hf Qwen/Qwen3-4B-GGUF:Q4_0 --port 8080` · verify `curl http://localhost:8080/v1/models` |
| Ollama 🔴 offline | `ollama serve` · then `ollama pull gemma3:4b` · verify `ollama list` |
| `That file doesn't look like a real PDF` | File isn't a PDF (renamed .txt/.html). Upload the original PDF |
| `PDF is 80 MB — limit is 50` | Split the PDF or raise `MAX_PDF_MB` in `.env` |
| `database is locked` | Rare now (WAL enabled). Stop other app instances, restart |
| Slow first answer | Normal — embedding model downloads once (~500 MB), then cached |
| `ModuleNotFoundError` | You forgot activation: `.\avenv\Scripts\Activate.ps1` (Win) or `source avenv/bin/activate` (Mac/Linux), reinstall requirements |

Clear all local memory: stop the app, delete `agentic_rag_memory.sqlite3` (chats/facts/cache/feedback go; vectors stay).

## Testing

```bash
python -m unittest discover -s tests -p 'test_*.py'   # Windows: "test_*.py"
python -m py_compile gradio_app.py agentic_docuchat/app.py agentic_docuchat/rag_backend.py agentic_docuchat/persistent_memory.py agentic_docuchat/ollama_utils.py agentic_docuchat/llamacpp_utils.py agentic_docuchat/prompt_engineering.py eval/evaluate.py
```

End-to-end needs a PDF + one working provider (Gemini key or local server).

## Security

- Never commit `.env`. Rotate leaked keys where you created them.
- Keep `GRADIO_SHARE=false` for private docs; strong password if you share.
- PDFs, chats, memories stay on your disk. Online embeddings/Gemini send text to Google.
- Rate limit is anti-double-click, not anti-abuse — don't expose unauthenticated.

## License

MIT — see [LICENSE](LICENSE). Educational and research use.

## How the backend works (for contributors)

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
app with the same PDF skips re-embedding entirely. Local models stream
token-by-token; the tool-calling agent path shows "Thinking…" instead.
Per-user rate limiting stops double-clicks queueing duplicate generations,
and startup validation catches bad config before your first question.

### Clear all local memory

Stop the app and remove the SQLite file:

```bash
rm agentic_rag_memory.sqlite3   # Windows: del agentic_rag_memory.sqlite3
```

This removes conversations, saved memories, cache entries, and feedback. Chroma vectors stay.
