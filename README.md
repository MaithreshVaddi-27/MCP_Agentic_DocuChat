<div align="center">

# MCP_Agentic_DocuChat

**Upload a PDF. Ask anything. Get answers that point to the page they came from.**

A local-first reading companion. Your documents, vectors, chats and memories stay on
your own disk. Runs fully offline against Ollama, llama.cpp or MLX; Gemini is optional.

`Python 3.10+` · `MIT` · `no API key required`

</div>

---

## What you get

| | |
|---|---|
| **Answers with receipts** | Every reply lists the exact pages it drew on. If the document does not say, the model says that instead of guessing. |
| **Three local runtimes** | Ollama, llama.cpp and MLX. Pick per question, switch from the UI. No cloud round trip unless you want one. |
| **Finds your models** | It asks each runtime what it has cached, so you get the exact command to start the one you already downloaded. |
| **Remembers context** | Durable facts are picked up automatically. Repeat questions come back instantly from cache. |
| **Resists prompt injection** | Text inside a PDF is treated as evidence, never as instructions. |
| **Nothing leaves the machine** | Local embeddings, local vector store, local chat history. |

---

## Contents

- [Quickstart](#quickstart) · [macOS](#macos) · [Linux](#linux) · [Windows](#windows)
- [Using an API key](#using-an-api-key)
- [Local models](#local-models)
- [Configuration](#configuration)
- [How it works](#how-it-works)
- [Project layout](#project-layout)
- [Testing](#testing) · [Evaluation](#evaluation) · [Production use](#production-use)
- [Troubleshooting](#troubleshooting)

---

## Quickstart

Every OS follows the same four steps. Pick yours below for the exact commands.

### macOS

Apple Silicon gets the best experience: all three local runtimes work, and MLX is
Metal-accelerated.

```bash
# 1. System tools
xcode-select --install          # only if you have never run it
brew install python@3.11 git

# 2. Clone and set up a virtual environment
git clone https://github.com/MaithreshVaddi-27/MCP_Agentic_DocuChat.git
cd MCP_Agentic_DocuChat
python3.11 -m venv venv
source venv/bin/activate

# 3. Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env            # optional, defaults work as-is

# 4. Run
python gradio_app.py
```

Then open <http://127.0.0.1:7860>, drop in a PDF, press **Process document**, and ask
*"What are the main findings?"*.

Local runtimes (all optional, install whichever you want):

```bash
brew install ollama                      # then: ollama serve
brew install llama.cpp                   # then: llama-server -hf <repo> --port 8080
pipx install mlx-lm                      # then: mlx_lm.server --model <repo> --port 8081
```

<details>
<summary>Apple Silicon: getting an Apple Silicon model for MLX</summary>

```bash
pipx install mlx-lm
mlx_lm.server --model mlx-community/Qwen3.5-2B-MLX-4bit --port 8081
```

`mlx_lm.manage --scan` lists what is already in the Hugging Face cache, so check
before you download anything.
</details>

### Linux

```bash
# 1. System packages
#    Ubuntu / Debian
sudo apt update && sudo apt install -y python3.11 python3.11-venv git build-essential
#    Fedora
sudo dnf install -y python3.11 python3.11-devel git gcc

# 2. Clone and set up
git clone https://github.com/MaithreshVaddi-27/MCP_Agentic_DocuChat.git
cd MCP_Agentic_DocuChat
python3.11 -m venv venv
source venv/bin/activate

# 3. Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env

# 4. Run
python gradio_app.py
```

On an NVIDIA GPU, install the CUDA build of PyTorch first so the embeddings use it:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

Local runtimes:

```bash
curl -fsSL https://ollama.com/install.sh | sh    # then: ollama serve
# llama.cpp: grab a release from
#   https://github.com/ggml-org/llama.cpp/releases
#   or build it:  git clone <repo> && cmake -B build && cmake --build build --config Release
```

<details>
<summary>Headless servers (no desktop)</summary>

Run it behind an SSH tunnel rather than exposing the port:

```bash
python gradio_app.py --server-name 127.0.0.1 --port 7860
# from your laptop
ssh -L 7860:127.0.0.1:7860 user@your-server
```

Set `GRADIO_USERNAME` and `GRADIO_PASSWORD` before anyone else can reach it.
</details>

### Windows

<details open>
<summary><strong>PowerShell</strong></summary>

```powershell
# 1. Check you have Python 3.10+
py -3.11 --version

# 2. Clone and set up
git clone https://github.com/MaithreshVaddi-27/MCP_Agentic_DocuChat.git
cd MCP_Agentic_DocuChat
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env

# 4. Run
python gradio_app.py
```
</details>

<details>
<summary><strong>Command Prompt (cmd.exe)</strong></summary>

```bat
git clone https://github.com/MaithreshVaddi-27/MCP_Agentic_DocuChat.git
cd MCP_Agentic_DocuChat
py -3.11 -m venv venv
venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
copy .env.example .env
python gradio_app.py
```
</details>

Install Python from [python.org](https://www.python.org/downloads/) and tick
**Add python.exe to PATH**. If activation is blocked by policy, run this once in an
Administrator PowerShell:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Local runtimes on Windows:

```powershell
winget install Ollama.Ollama      # then: ollama serve
# llama.cpp: download a release zip from
#   https://github.com/ggml-org/llama.cpp/releases
```

<details>
<summary>Windows: long paths</summary>

PDF parsing can exceed the default 260-character path limit. Enable long paths once,
as Administrator:

```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```
</details>

---

## Using an API key

You do not need one. Everything above runs on your own hardware.

If you would rather use **Google Gemini**, here is the whole process.

**1. Get a key.** Go to
[<https://aistudio.google.com/apikey>](https://aistudio.google.com/apikey), sign in
with a Google account, and click **Create API key**. Pick an existing Google Cloud
project or let it make one for you. The key is shown once, so copy it straight away.

**2. Put it in `.env`.** In the project folder:

```bash
cp .env.example .env      # macOS / Linux
Copy-Item .env.example .env   # Windows PowerShell
```

Find the line and paste your key after the `=`, with no quotes and no spaces:

```dotenv
GEMINI_API_KEY=AIzaSy...your-key-here
GEMINI_MODEL=gemini-3.5-flash-lite
```

**3. Check it took.** This prints a green line if the key works:

```bash
python -m agentic_docuchat.llm.models
```

Then choose **Gemini** in the app's Provider dropdown.

<details>
<summary>Two things worth knowing</summary>

**Keep the key out of git.** `.env` is already in `.gitignore`; only `.env.example`
is tracked. If a key ever lands in a commit, revoke it at
[aistudio.google.com/apikey](https://aistudio.google.com/apikey) immediately and
create a new one.

**Free tier has a rate limit.** The default model is the cheapest one that still
answers grounded questions well. If you hit a quota, either wait, enable billing in
AI Studio, or switch back to a local model. Nothing breaks either way.
</details>

You can also set `EMBEDDING_PROVIDER=online` to use Google's embeddings instead of the
local one. That needs the same key, and it is the only setting that sends document
text to a third party.

---

## Local models

The app talks to three OpenAI-compatible runtimes. Start whichever one you want; it
finds the runtime, lists what that runtime serves, and lets you switch between them
without restarting.

| Runtime | Install | Start | Default URL |
|---------|---------|-------|-------------|
| **Ollama** | [ollama.com/download](https://ollama.com/download) | `ollama serve` | `http://localhost:11434` |
| **llama.cpp** | [releases](https://github.com/ggml-org/llama.cpp/releases) | `llama-server -hf <repo> --port 8080` | `http://localhost:8080/v1` |
| **MLX** (Apple Silicon) | `pipx install mlx-lm` | `mlx_lm.server --model <repo> --port 8081` | `http://localhost:8081/v1` |
| **Gemini** (optional) | see [above](#using-an-api-key) | managed | managed |

### Finding what you already have

```bash
python -m agentic_docuchat.llm.models
```

This is the fastest way to answer *"which model should I point this at?"*. It probes
each runtime **and** reads what is cached on disk, so it still tells you what you have
when nothing is running yet:

```text
ollama (http://localhost:11434): running — qwen3:1.7b, gemma3:1b
llamacpp (http://localhost:8080/v1): offline — 3 model(s) already on disk: ggml-org/SmolLM3-3B-GGUF:Q4_K_M, ...
mlx (http://127.0.0.1:8081/v1): offline — 7 model(s) already on disk: mlx-community/gemma-3-4b-it-4bit, ...

No provider is serving right now. Start one:
  ollama    -> ollama serve
  llamacpp  -> llama-server -hf ggml-org/SmolLM3-3B-GGUF:Q4_K_M --port 8080
  mlx       -> mlx_lm.server --model mlx-community/gemma-3-4b-it-4bit --port 8081
```

Discovery asks each runtime to inventory itself rather than guessing at its storage
layout:

| Runtime | Command | Works with nothing running? |
|---------|---------|----------------------------|
| Ollama | `ollama list` | needs the daemon |
| llama.cpp | `llama-server --cache-list` | yes |
| MLX | `mlx_lm.manage --scan` | yes |

Where a command is missing, discovery falls back to reading the known cache layout
(the Hugging Face hub plus anything in `LLAMACPP_MODEL_DIRS`). Repos whose download
never finished are filtered out, so nothing listed here will fail to load. The same
information shows in the app's status panel.

The first run downloads one embedding model, about 1.3 GB, then caches it. Every
later run starts instantly.

---

## Configuration

Everything lives in `.env`. Restart the app after changing anything. PDFs are not
configured here; you upload them through the UI.

### The ones you will actually change

| Variable | Default | What it does |
|----------|---------|--------------|
| `OLLAMA_MODEL` / `OLLAMA_BASE_URL` | `gemma3:4b` / `http://localhost:11434` | Ollama runtime |
| `LLAMACPP_MODEL` / `LLAMACPP_BASE_URL` | `Qwen3-4B-GGUF:Q4_0` / `http://localhost:8080/v1` | llama.cpp runtime |
| `MLX_MODEL` / `MLX_BASE_URL` | `mlx-community/gemma-3-4b-it-4bit` / `http://localhost:8081/v1` | MLX runtime |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | — / `gemini-3.5-flash-lite` | Gemini provider |
| `EMBEDDING_PROVIDER` | `local` | `local` keeps embeddings on your machine; `online` uses Google's |
| `RETRIEVAL_K` / `RETRIEVAL_FETCH_K` | `4` / `12` | How many passages reach the model, and the candidate pool they are chosen from |
| `MAX_PDF_MB` | `50` | Upload size cap |
| `GRADIO_USERNAME` / `GRADIO_PASSWORD` | placeholders, login off | Require a login |
| `GRADIO_SHARE` | `false` | `true` creates a temporary public URL and refuses to start without a login |

### The rest

[`.env.example`](.env.example) documents all 44 variables, grouped and commented:
provider timeouts, chunking, cache bounds, storage paths, rate limiting and logging.
Every `os.getenv` in the source has a matching entry there.

---

## How it works

1. **You upload a PDF.** Pages are split into overlapping chunks, embedded locally and
   stored in Chroma. Uploads are checked by extension, `%PDF-` header and size.
2. **You ask a question.** One MMR search pulls the best passages. That single search
   feeds both the model and the Sources box, so the two can never disagree.
3. **The model answers from an evidence pack.** Retrieved text is labelled as evidence
   and never as instructions, so a PDF containing *"ignore your previous instructions"*
   does not get to give any.
4. **Answers get checked.** If a draft cites no page and does not admit a gap, it gets
   one repair pass. If that repair comes back empty, the original draft is kept.
5. **Memory and cache are written** to one local SQLite file. Durable facts are picked
   up on their own ("I prefer short answers"), and a repeated question comes straight
   back.

Each document gets its own Chroma collection, keyed on a fingerprint of the file and
the active embedding model. That means vectors from different documents never mix,
re-opening the same PDF skips re-embedding, and superseded collections are swept
instead of piling up.

---

## Project layout

```text
MCP_Agentic_DocuChat/
├── gradio_app.py                 # launcher: python gradio_app.py
├── agentic_docuchat/
│   ├── app.py                    # Gradio UI, the composition root
│   ├── rag/
│   │   ├── backend.py            # indexing, providers, retrieval, agent
│   │   ├── memory.py             # local SQLite: chats, facts, answer cache
│   │   └── prompts.py            # evidence packs and grounding repair
│   ├── llm/
│   │   ├── discovery.py          # on-disk model discovery for all three runtimes
│   │   ├── ollama.py             # health probes
│   │   ├── llamacpp.py
│   │   ├── mlx.py
│   │   └── models.py             # python -m agentic_docuchat.llm.models
│   └── mcp/
│       └── tools.py              # Composio loader, lazy and fail-closed
├── eval/evaluate.py              # DeepEval quality suite
├── tests/                        # 101 unit tests
└── pyproject.toml · requirements.txt · .env.example
```

Runtime output is git-ignored: `.env`, `data/uploads/`, `chroma_langchain_db/`,
`*.sqlite3`, `__pycache__/`.

---

## Testing

```bash
python -m ruff check .                                # lint gate
python -m compileall -q gradio_app.py agentic_docuchat eval tests
python -m unittest discover -s tests -p 'test_*.py'  # 101 tests
```

The suite builds throwaway Ollama and Hugging Face layouts in temporary directories,
so it never depends on which models happen to be installed on the machine running it.
Tests that need the full LangChain stack skip themselves cleanly in a light
environment.

CI runs this on Python 3.10 to 3.12, checks that the app boots with no document
loaded, and builds and installs a wheel.

---

## Evaluation

```bash
python eval/evaluate.py --document ./data/uploads/your.pdf --provider llamacpp
# providers: llamacpp | ollama | mlx | gemini
```

Scores 0 to 1 on faithfulness (are the claims actually in the document), answer
relevancy, and context precision (were the right pages retrieved), across four fixed
questions. One of them is unanswerable on purpose, to check the model admits it.
With `GEMINI_API_KEY` set, DeepEval's judge does the scoring; without a key it falls
back to offline citation checks so the run still works anywhere. Aim for faithfulness
above 0.80.

---

## Production use

A few things that matter once this is more than a personal tool.

**Lock the UI down.** `GRADIO_SHARE` is `false` by default. Setting
`GRADIO_USERNAME` and `GRADIO_PASSWORD` turns login on everywhere, and public sharing
without them is refused at startup. Do not put an unauthenticated Gradio port on a
network you do not trust; use an SSH tunnel or an authenticated reverse proxy. The
per-user rate limit stops double-clicks, not attackers.

**Know what to back up.**

| Path | Holds |
|------|-------|
| `agentic_rag_memory.sqlite3` | Chats, remembered facts, answer cache |
| `data/uploads/` | Your PDFs |
| `chroma_langchain_db/` | Vectors |

Everything else rebuilds itself.

**Pin before you upgrade.** Dependencies are pinned in `requirements.txt`.
`langchain-openai` must stay on 1.x: the 0.3.x line caps `langchain-core<1.0` and
conflicts with the LangChain 1.x family. After any bump, run the
[testing](#testing) commands and ask one real question against a real PDF.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Ollama shows offline | `ollama serve`, then `ollama pull gemma3:4b`. `python -m agentic_docuchat.llm.models` shows what you already have. |
| llama.cpp shows offline | `llama-server -hf ggml-org/SmolLM3-3B-GGUF --port 8080`. Check with `curl http://localhost:8080/v1/models`. |
| MLX shows offline | `mlx_lm.server --model mlx-community/gemma-3-4b-it-4bit --port 8081`. Check with `curl http://localhost:8081/v1/models`. |
| `not installed — pick one below` | The configured model is not on that server. Choose a real one from the **Local model** dropdown. |
| `No document loaded` | Expected on a fresh clone. Upload a PDF and press **Process document**. |
| `That file doesn't look like a real PDF` | A renamed `.txt` or `.html`. Upload the original PDF. |
| `PDF is 80 MB — limit is 50` | Split the file, or raise `MAX_PDF_MB`. |
| The answer box shows `…` and never finishes | The provider is streaming empty chunks. Check its log. A reasoning model that runs out of token budget answers in a separate field; pick a non-thinking model or raise the server's budget with `--max-tokens`. |
| `The model returned an empty answer` | Same cause, now reported instead of hanging. Raise the server's token budget or use a model without a thinking mode. |
| `GEMINI_API_KEY is missing` | Add a key from [AI Studio](https://aistudio.google.com/apikey) to `.env`. |
| `database is locked` | Rare, since WAL is on. Close other instances and restart. |
| The first answer is slow | Normal. The embedding model is downloading once, about 1.3 GB, then cached. |
| `pip install` conflicts | Use `requirements.txt` as pinned. See [Production use](#production-use). |
| `ModuleNotFoundError` | The virtual environment is not active, or the install failed. Re-activate and reinstall. |

---

## Contributing

Small, focused pull requests, and a test that fails before your change and passes
after it. Full guide in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Security

Keep `.env` out of git. Keep sharing off for private documents. PDFs, chats and
memories stay local unless you turn on online embeddings or Gemini. Report
vulnerabilities privately rather than as a public issue: [`SECURITY.md`](SECURITY.md).

## License

MIT, see [`LICENSE`](LICENSE). Built for study, research and personal use.
