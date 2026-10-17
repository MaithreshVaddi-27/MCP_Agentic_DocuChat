<div align="center">

# MCP_Agentic_DocuChat

**Upload a PDF. Ask a question. Get an answer that names the pages it came from.**

A local-first reading companion. Your documents, embeddings, chat history and
memories stay on your own disk. Runs fully offline against Ollama, llama.cpp or
MLX — Google Gemini is there if you'd rather not run anything locally.

`Python 3.10+` · `MIT` · `no API key required`

[![CI](https://github.com/MaithreshVaddi-27/MCP_Agentic_DocuChat/actions/workflows/ci.yml/badge.svg)](https://github.com/MaithreshVaddi-27/MCP_Agentic_DocuChat/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![No API key needed](https://img.shields.io/badge/API_key-not_required-brightgreen.svg)](#option-b-use-google-gemini)

</div>

---

Most chat tools will summarise a document and hope you don't notice it invented
something. This one doesn't get that option. Every answer is grounded in
retrieved passages and ends with a **Sources** list naming the exact pages. When
the document doesn't contain the answer, the model is told to say so instead of
filling the gap.

> [!TIP]
> **The fastest way in:** if you just want to read a paper, start
> [Ollama](https://ollama.com/download), pull a small model, and run the app.
> No key, no account, nothing leaves your machine.

---

## What you get

| | |
|---|---|
| **Answers with receipts** | Every reply lists the pages it drew on. With no page citation there is no answer; the app rewrites the draft once before giving up. |
| **Three local runtimes** | Ollama, llama.cpp and MLX. Switch per question from the UI. No cloud round trip unless you ask for one. |
| **It finds your models** | Asks each runtime what it has cached and prints the exact command to start the one you already downloaded. |
| **Remembers context** | Durable facts are picked up automatically. Repeat questions come back instantly from a local cache. |
| **Resists prompt injection** | Text inside a PDF is treated as evidence, never as instructions. |
| **Survives a bad start** | A missing model server, an unconfigured toolkit or a broken runtime degrades to a message, never a crash. |
| **Nothing leaves the machine** | Local embeddings, local vector store, local chat history. The one exception is opt-in. |

---

## Contents

- [Requirements](#requirements)
- [Setup](#setup) — [macOS](#macos) · [Linux](#linux) · [Windows](#windows)
- [Choose how to answer](#choose-how-to-answer)
- [Your first run](#your-first-run)
- [Using the app](#using-the-app)
- [Option B: use Google Gemini](#option-b-use-google-gemini)
- [Finding models you already have](#finding-models-you-already-have)
- [Configuration](#configuration)
- [How it works](#how-it-works)
- [Project layout](#project-layout)
- [Testing](#testing) · [Evaluation](#evaluation)
- [Troubleshooting](#troubleshooting)
- [Security notes](#security-notes)

---

## Requirements

Three things. You probably have two already.

1. **Python 3.10, 3.11, 3.12 or 3.13.** Tested on all four.
2. **A few GB of free disk.** The embedding model downloads once (~1.3 GB) and
   is cached after that. Each chat model you add is a few GB more.
3. **One way to run a model** — pick either:
   - **A local runtime.** [Ollama](https://ollama.com/download) is the easiest
     single install; llama.cpp and MLX work too.
   - **A free Google Gemini key.** [About five minutes.](#option-b-use-google-gemini)

That is the only real decision. Everything else has a default that works offline.

---

## Setup

Every platform is the same four steps: create a virtual environment, install
dependencies, optionally copy the env file, run. Pick your OS for exact commands.

> [!IMPORTANT]
> **Use a virtual environment.** Without one, `pip install` either fails or, on
> a Homebrew Python, installs into the system interpreter. Every command below
> assumes you are inside the venv.

### macOS

Apple Silicon gets the best experience: all three local runtimes work, and MLX
is Metal-accelerated.

```bash
# 1. System tools
xcode-select --install          # only if you have never run it
brew install python@3.11 git

# 2. Clone and create the virtual environment
git clone https://github.com/MaithreshVaddi-27/MCP_Agentic_DocuChat.git
cd MCP_Agentic_DocuChat
python3.11 -m venv venv
source venv/bin/activate

# 3. Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env             # optional — defaults run fully offline

# 4. Run
python gradio_app.py
```

Then open <http://127.0.0.1:7860>, drop in a PDF, press **Process document**, and
ask *"What are the main findings?"*.

<details>
<summary>Local runtimes on macOS (all optional — install whichever you want)</summary>

```bash
brew install ollama                      # then: ollama serve
brew install llama.cpp                   # then: llama-server -hf <repo> --port 8080
pipx install mlx-lm                      # then: mlx_lm.server --model <repo> --port 8081
```

</details>

<details>
<summary>Apple Silicon: which MLX model to start with</summary>

```bash
pipx install mlx-lm
mlx_lm.manage --scan                                           # check the cache first
mlx_lm.server --model mlx-community/Llama-3.2-1B-Instruct-4bit --port 8081
```

`--scan` lists what is already downloaded, so check before fetching anything.

</details>

### Linux

```bash
# 1. System packages
#    Ubuntu / Debian
sudo apt update && sudo apt install -y python3.11 python3.11-venv git build-essential

#    Fedora
sudo dnf install -y python3.11 python3.11-devel git gcc

# 2. Clone and create the virtual environment
git clone https://github.com/MaithreshVaddi-27/MCP_Agentic_DocuChat.git
cd MCP_Agentic_DocuChat
python3.11 -m venv venv
source venv/bin/activate

# 3. Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env             # optional

# 4. Run
python gradio_app.py
```

<details>
<summary>NVIDIA GPU (optional — much faster local answers)</summary>

The default PyTorch wheel is fine on CPU. To use CUDA instead:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

Ollama ships its own GPU detection and needs none of this.

</details>

<details>
<summary>Headless servers (optional)</summary>

```bash
sudo apt install -y poppler-utils      # pdftotext, handy for inspecting PDFs
```

Not required. The app reads PDFs itself; it is listed only in case you want it
for debugging a document that will not parse.

</details>

### Windows

```powershell
# 1. Check you have Python 3.10+ (the py launcher is installed by default)
py -3.11 --version

# 2. Clone and create the virtual environment
git clone https://github.com/MaithreshVaddi-27/MCP_Agentic_DocuChat.git
cd MCP_Agentic_DocuChat
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env    # optional

# 4. Run
python gradio_app.py
```

<details>
<summary>If PowerShell blocks the activate script</summary>

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Or skip activation entirely and call the venv's Python directly:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe gradio_app.py
```

</details>

<details>
<summary>Local runtimes on Windows (optional)</summary>

```powershell
winget install Ollama.Ollama        # then, in another terminal: ollama serve
```

llama.cpp and MLX work on Windows too, but MLX needs Apple Silicon, so on
Windows your realistic local options are Ollama and llama.cpp.

</details>

---

## Choose how to answer

| Your machine | Easiest path | Why |
|---|---|---|
| Apple Silicon Mac | MLX or Ollama | MLX is Metal-accelerated; Ollama is a single install |
| Linux with NVIDIA GPU | Ollama | Ships its own GPU detection |
| Windows | Ollama via `winget` | No build tools required |
| Anything, no installs | Gemini | Free key, nothing runs locally |

You can switch providers per question from the dropdown. No restart needed.

The app speaks to three OpenAI-compatible runtimes. Start whichever one you want;
it detects the runtime, lists what that runtime serves, and lets you switch
without restarting.

| Runtime | Install | Start | Default URL |
|---------|---------|-------|-------------|
| **Ollama** | [ollama.com/download](https://ollama.com/download) | `ollama serve` | `http://localhost:11434` |
| **llama.cpp** | [releases](https://github.com/ggml-org/llama.cpp/releases) | `llama-server -hf <repo> --port 8080` | `http://localhost:8080/v1` |
| **MLX** (Apple Silicon) | `pipx install mlx-lm` | `mlx_lm.server --model <repo> --port 8081` | `http://localhost:8081/v1` |
| **Gemini** (optional) | see [below](#option-b-use-google-gemini) | managed | managed |

<details>
<summary>Starting Ollama — the easiest path</summary>

```bash
ollama serve                    # start the server, keep this terminal open
ollama pull gemma3:4b           # download a model, first time only (~3 GB)
ollama list                     # confirm it is there
curl http://localhost:11434/api/tags   # check it is answering
```

In the app: **Provider → Ollama**, then pick the model from **Local model**.
`ollama pull <name>` fetches any other model; `ollama list` always shows what you
have. On a small machine, `qwen3:1.7b` (1.4 GB) is a lighter alternative.

</details>

<details>
<summary>Starting llama.cpp — good on CPU-only machines</summary>

```bash
llama-server --cache-list       # what is already cached; works with no server running
llama-server -hf second-state/SmolLM2-1.7B-Instruct-GGUF:Q4_K_M --port 8080
curl http://localhost:8080/v1/models   # check it is answering
```

In the app: **Provider → Llama.cpp**, then pick the served model. The `-hf`
value is `<user>/<repo>[:quant]`; any GGUF repo works, and an already-cached one
starts with no download.

</details>

<details>
<summary>Starting MLX — Apple Silicon only</summary>

```bash
pipx install mlx-lm              # once
mlx_lm.manage --scan             # what is already in the Hugging Face cache
mlx_lm.server --model mlx-community/Llama-3.2-1B-Instruct-4bit --port 8081
curl http://localhost:8081/v1/models   # check it is answering
```

In the app: **Provider → MLX**, then pick the served model.

</details>

> [!NOTE]
> The model server runs in a **separate terminal** and must stay open while you
> chat. Closing it does not break anything; the app reports the runtime as
> offline and tells you how to start it again.

---

## Your first run

You have installed it and `python gradio_app.py` is running.

1. **Open <http://127.0.0.1:7860>.** A setup column on the left, an empty
   conversation on the right.
2. **Read the status panel.** On a fresh start it says no document is loaded.
   That is the normal state, not an error. The app is waiting for your first PDF.
3. **Start a model server** in another terminal (e.g. `ollama serve`), or choose
   **Gemini** and add a key.
4. **Upload a PDF and press Process document.** The first run downloads the
   embedding model (~1.3 GB), so give it a couple of minutes. Every later
   document starts instantly, and reopening the app with the same PDF skips
   re-embedding entirely.
5. **Ask *"What are the main findings?"*** The answer arrives with a **Sources**
   list naming the pages it came from.

---

## Using the app

The left column is setup, the right side is the conversation. Everything you
might change mid-session is there.

| Control | What it does |
|---|---|
| **User ID** | Scopes memory, rate limiting and the answer cache. Change it to get a separate notebook. |
| **Provider** | Gemini, Ollama, Llama.cpp or MLX. Switch per question. |
| **Local model** | Lists what the running server actually reports. No restart needed to switch models. |
| **Embeddings** | `Local` (on this machine) or `Online` (Google's API). See [the privacy note](#configuration). |
| **Upload a PDF** → **Process document** | Reads, chunks and indexes the file. |
| **Rebuild index** | Forces a fresh embed. Needed after changing chunking or the embedding model. |
| 👍 / 👎 | Records feedback against the answer, stored locally. |
| **Clear my chat & memory** | Wipes this User ID's history, saved facts and cached answers. |
| **Export chat** | Downloads the transcript. |

### A few behaviours worth knowing

**Repeats are instant.** A question you already asked comes back from a local
cache keyed on your saved memories and the document, not on the chat history,
which would change on every turn and never match. Useful when you are
re-reading the same paper.

**Answers are checked before you see them.** If a draft comes back with no page
citation, the app hands it to the same model once more with a "fix this using
only the evidence" note. If that repair returns nothing, you keep the original
draft rather than an empty answer. Tune with `ANSWER_LOOP_MAX_ATTEMPTS`.

**Local models stream; Gemini does not.** With no MCP tools configured, Ollama
and llama.cpp stream tokens as they generate. The Gemini path runs as a
tool-calling agent, which does not stream cleanly, so it returns in one go.

**Nothing is configured by document path.** You upload PDFs through the UI.
`data/` is git-ignored, so your documents never reach the repository.

---

## Option B: use Google Gemini

You do not need a key for anything above. If you would rather use **Google
Gemini**, this is the whole process.

**1. Get a key.** Go to
[<https://aistudio.google.com/apikey>](https://aistudio.google.com/apikey), sign in
with a Google account, click **Create API key**, and pick an existing Google Cloud
project or let it make one. The key is shown once; copy it immediately.

**2. Put it in `.env`.** In the project folder:

```bash
cp .env.example .env             # macOS / Linux
Copy-Item .env.example .env      # Windows PowerShell
```

Paste your key after the `=`, with no quotes and no spaces:

```dotenv
GEMINI_API_KEY=AIzaSy...your-key-here
```

**3. Check it took.**

```bash
python -m agentic_docuchat.llm.models
```

Then choose **Gemini** in the app's Provider dropdown.

> [!WARNING]
> **Keep the key out of git.** `.env` is already in `.gitignore`; only
> `.env.example` is tracked. If a key ever lands in a commit, revoke it at
> [aistudio.google.com/apikey](https://aistudio.google.com/apikey) right away and
> create a new one.

The free tier is rate-limited. If you hit a quota, enable billing in AI Studio or
switch back to a local model; nothing breaks either way.

---

## Finding models you already have

This is the fastest way to answer *"which model should I point this at?"*

```bash
python -m agentic_docuchat.llm.models
```

It probes each runtime **and** reads what is cached on disk, so it still tells
you what you have when nothing is running:

```text
ollama (http://localhost:11434): offline. 2 model(s) already on disk: gemma3:1b, qwen3:1.7b
llamacpp (http://localhost:8080/v1): offline. 3 model(s) already on disk: LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M, ggml-org/SmolLM3-3B-GGUF:Q4_K_M, second-state/SmolLM2-1.7B-Instruct-GGUF:Q4_K_M
mlx (http://localhost:8081/v1): offline. 7 model(s) already on disk: lmstudio-community/LFM2.5-2.6B-MLX-4bit, mlx-community/LFM2.5-1.2B-Instruct-OptiQ-4bit, mlx-community/Llama-3.2-1B-Instruct-4bit, mlx-community/Qwen3-4B-Instruct-2507-4bit (+3 more)

No provider is serving right now. Start one:
  ollama serve
  llama-server -hf LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M --port 8080
  mlx_lm.server --model lmstudio-community/LFM2.5-2.6B-MLX-4bit --port 8081
```

Discovery asks each runtime to inventory itself rather than guessing at its
storage layout:

| Runtime | Command used | Works with nothing running? |
|---------|---------------|----------------------------|
| Ollama | `ollama list` | needs the daemon |
| llama.cpp | `llama-server --cache-list` | yes |
| MLX | `mlx_lm.manage --scan` | yes |

Where a command is missing, discovery falls back to reading the known cache
layout (the Hugging Face hub plus anything in `LLAMACPP_MODEL_DIRS`). Partially
downloaded repos are filtered out, so nothing listed here will fail to load.
The same information appears in the app's status panel.

---

## Configuration

Everything lives in `.env`. Restart the app after changing anything. PDFs are
never configured here. You upload them through the UI.

### The ones you will actually change

| Variable | Default | What it does |
|----------|---------|--------------|
| `OLLAMA_MODEL` / `OLLAMA_BASE_URL` | `gemma3:4b` / `http://localhost:11434` | Ollama runtime |
| `LLAMACPP_MODEL` / `LLAMACPP_BASE_URL` | `Qwen3-4B-GGUF:Q4_0` / `http://localhost:8080/v1` | llama.cpp runtime |
| `MLX_MODEL` / `MLX_BASE_URL` | `mlx-community/gemma-3-4b-it-4bit` / `http://localhost:8081/v1` | MLX runtime |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | — / see `.env.example` | Gemini provider |
| `EMBEDDING_PROVIDER` | `local` | `local` keeps embeddings on your machine; `online` uses Google's |
| `EMBEDDING_MODEL` | `BAAI/bge-large-en-v1.5` | Only used when `EMBEDDING_PROVIDER=local` |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `700` / `100` | How the document is split. Rebuild the index after changing these. |
| `RETRIEVAL_K` / `RETRIEVAL_FETCH_K` | `4` / `12` | Passages reaching the model, and the candidate pool they are chosen from |
| `MAX_PDF_MB` | `50` | Upload size cap |
| `GRADIO_USERNAME` / `GRADIO_PASSWORD` | placeholders, login off | Require a login |
| `GRADIO_SHARE` | `false` | `true` creates a temporary public URL and refuses to start without a login |
| `COMPOSIO_API_KEY` / `COMPOSIO_TOOLKITS` | — / `TAVILY` | Optional web tools. Blank means pure-document mode. |

> [!IMPORTANT]
> **`EMBEDDING_PROVIDER=online` is the only setting that sends document text to a
> third party.** Everything else (local providers, local embeddings, the local
> vector store, local chat history) stays on your machine. Leave it on `local`
> unless you have a reason not to.

[`.env.example`](.env.example) documents all 43 variables, grouped and
commented: provider endpoints, chunking, cache bounds, storage paths, rate
limiting, access control and logging. Every `os.getenv` in the source has a
matching entry there.

---

## How it works

The whole path, in the order it happens.

1. **Upload.** The file is checked three ways: extension, a `%PDF-` magic-byte
   header, and a size cap. A renamed `.txt` fails with a readable message instead
   of an exception from deep inside a PDF parser.
2. **Index.** Pages are split into overlapping 700-character chunks and embedded.
   Local embeddings go through a Hugging Face sentence-transformer; the model
   is cached on disk after the first download.
3. **Name the collection.** The Chroma collection is derived from a fingerprint
   of the file path, its size and mtime, *and* the embedding model in use.
   Vectors from different documents or different embedding spaces are not
   comparable, so this makes it impossible to silently answer from a stale
   index. Superseded collections under our own prefix are swept on success.
4. **Retrieve.** One MMR search returns the best passages. That single search
   feeds both the model and the Sources box, so the two can never disagree.
5. **Assemble the context.** A CRAFT prompt (Context, Role, Action, Format,
   Target) is packed using TOON (Token-Oriented Object Notation), which
   declares `{source, page, text}` once per row instead of repeating the keys
   per chunk. That is where most of the token saving comes from.
6. **Answer, then verify.** The draft is checked for a page citation. If it has
   none, it goes back to the model once with a repair note. An empty repair
   result keeps the original draft rather than replacing it with nothing.
7. **Remember.** The turn is written to SQLite, short facts you stated are
   captured, and the answer is cached against your saved memories.

### Things that make it feel fast

- Retrieval runs **at most once** per question, shared by the answer and Sources.
- The embedding model and chat model are built **once** and reused.
- Runtime health checks are cached for a few seconds, not re-probed per message.
- Reopening the app with the same PDF **skips re-embedding entirely**.
- Model calls retry with exponential backoff, because local servers routinely
  hiccup while loading a model.

### Graceful degradation

A missing dependency or a dead server should never take the UI down. Each one
degrades to a message instead:

| Failure | What happens |
|---|---|
| Model server not running | The provider line says offline and prints the command to start it. |
| Configured model not installed | Names the near-miss (`gemma3:1b` for a `gemma3:4b` config) instead of letting a raw 404 through. |
| Optional provider package missing | A `RuntimeError` naming the exact `pip install` that fixes it. |
| Composio unconfigured or failing | Web tools silently become an empty list. Retrieval is unaffected. |
| Answer comes back empty | Explains that a reasoning model likely spent its budget, and suggests a non-thinking model. |
| Chroma unhappy during housekeeping | Warns and moves on; a stale collection on disk beats a failed index build. |
| No document loaded | The normal state of a fresh clone. The model picker, status and memory controls still work. |

---

## Project layout

```text
MCP_Agentic_DocuChat/
├── gradio_app.py               # entry point (the only file you run directly)
├── agentic_docuchat/
│   ├── app.py                  # Gradio UI, event wiring, launch config
│   ├── llm/
│   │   ├── discovery.py        # per-runtime model discovery + health probes
│   │   ├── models.py           # `python -m` model probe CLI
│   │   ├── ollama.py           # Ollama runtime adapter
│   │   ├── llamacpp.py         # llama.cpp runtime adapter
│   │   └── mlx.py              # MLX runtime adapter
│   ├── rag/
│   │   ├── backend.py          # indexing, retrieval, providers, answer loop
│   │   ├── memory.py           # SQLite notebook + response cache
│   │   └── prompts.py          # CRAFT prompts, TOON context packing
│   └── mcp/
│       └── tools.py            # Composio loading, fully isolated
├── eval/evaluate.py            # optional DeepEval quality harness
├── tests/                      # 102 tests, self-contained
└── .env.example                # every configuration variable, documented
```

`agentic_docuchat/rag/backend.py` is the single source of truth for behaviour.
New work extends it rather than introducing a parallel CLI or agent flow.

---

## Testing

```bash
python -m ruff check .                                # lint gate
python -m compileall -q gradio_app.py agentic_docuchat eval tests
python -m unittest discover -s tests -p 'test_*.py'   # 102 tests
```

The suite builds throwaway Ollama and Hugging Face layouts in temporary
directories, so it never depends on which models happen to be installed on the
machine running it. Tests needing the full LangChain stack skip themselves
cleanly in a light environment.

CI runs this on Python 3.10 through 3.13, checks that the app boots with no
document loaded, and builds and installs a wheel.

---

## Evaluation

Optional, and only needed if you want numbers rather than vibes.

```bash
python eval/evaluate.py --document path/to/your-paper.pdf --provider llamacpp
```

`--document` is required. The eval scores a specific PDF against a built-in
golden question set. `--provider` accepts `gemini`, `ollama`, `llamacpp` or
`mlx` and defaults to `llamacpp`. Results cover faithfulness, answer relevancy
and context precision.

With `GEMINI_API_KEY` set, DeepEval's judge does the scoring; without a key it
falls back and tells you so.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `pip install` conflicts | Use `requirements.txt` as pinned. See [Configuration](#configuration). |
| `externally-managed-environment` | You are not in the venv. `source venv/bin/activate` and retry. |
| App starts, but every question says no document | Press **Process document** after uploading. |
| First document takes forever | It is downloading the ~1.3 GB embedding model once. Later documents are instant. |
| "Ollama model `x` is not installed" | `ollama pull x`, or pick an installed model from the dropdown. |
| "llama.cpp server is not reachable" | Start it in another terminal: `llama-server -hf <repo> --port 8080`. |
| "EMBEDDING_PROVIDER=online requires GEMINI_API_KEY" | Add the key, or switch embeddings back to `local`. |
| Answers have no Sources | Set `ANSWER_LOOP_MAX_ATTEMPTS=2` and rebuild the index. |
| Answers feel ungrounded | Raise `RETRIEVAL_K`, or use a larger chat model. |
| Changed chunking, nothing changed | Press **Rebuild index**. The index is not automatic. |
| Switching models changes nothing | Press **Refresh status** in the status panel. |
| Slow on Apple Silicon | Use MLX instead of Ollama. |

For anything not listed here, the probe is the fastest first step:

```bash
python -m agentic_docuchat.llm.models
```

---

## Security notes

Short version; the full policy is in [SECURITY.md](SECURITY.md).

- The Gradio UI has **no login by default**. Set `GRADIO_USERNAME` and
  `GRADIO_PASSWORD` before exposing it to any network you do not trust.
  `GRADIO_SHARE=true` refuses to start without them.
- The per-user rate limit is **in-memory**: it stops double-clicks, not
  attackers.
- PDFs are validated by extension, magic bytes and size, **not** malware
  scanned. Do not process untrusted PDFs on a sensitive machine.
- Report vulnerabilities privately. **Do not open a public issue.**

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). In short: virtual environment first,
`ruff` clean, tests green, and a test that fails without your change. If you
touch a provider, live-check it against the real runtime with
`python -m agentic_docuchat.llm.models`.

[MIT licensed](LICENSE).
