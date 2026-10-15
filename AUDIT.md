# Deep audit — MCP_Agentic_DocuChat

Audited 2026-10-15 against `main` @ `035e0e7`, on macOS with Python 3.12.15,
using a virtual environment built from scratch from `requirements.txt`.

Every claim below was checked by running the command shown, not by reading.

## Critical issues found and fixed

### 1. CI was failing on every Python version

`ci.yml` ran `python -m ruff check .`, but nothing ever installed ruff.
The workflow installs `requirements.txt` and stops there, and ruff was not in
that file. The lint step therefore exited non-zero on 3.10, 3.11 and 3.12.

The problem was invisible locally because ruff had been installed by hand into
a long-lived virtual environment at some point.

This was proven, not guessed: a virtual environment built only from
`requirements.txt` reported `No module named ruff`.

**Fixed** by pinning `ruff==0.17.0` in `requirements.txt` under a new
`development` section, so the existing `pip install -r requirements.txt` step
supplies it and `CONTRIBUTING.md` works for a first-time contributor. Re-ran
the exact CI sequence afterwards; the lint step passes.

### 2. Two dependencies were pinned but never used

- `requests==2.34.2` — nothing imports it. It was left behind when the HTTP
  probe in `backend.py` was simplified.
- `pytest==8.3.5` — the suite is `unittest.TestCase` throughout. CI, README and
  CONTRIBUTING all run `python -m unittest discover`. Nothing invokes pytest,
  and `pyproject.toml` carried a `[tool.pytest.ini_options]` section configuring
  a runner that is never used.

Both still arrive transitively (requests via gradio/composio, pytest via
deepeval), which confirms the explicit pins were redundant rather than load
bearing. Removing them changed nothing at runtime.

**Fixed** by dropping both pins and deleting the dead pytest config section.

### 3. Docstrings named modules deleted in v3.0

`llm/mlx.py` and `llm/llamacpp.py` both said their return shape matches
`ollama_utils.ollama_status()`. That module no longer exists; it is
`llm/ollama.py` now. Anyone reading those docstrings to learn the contract was
being pointed at a dead path.

**Fixed** — both now reference `llm.ollama.ollama_status()`.

## Checks that passed

| Area | Method | Result |
| --- | --- | --- |
| Lint | `ruff check .` (E4,E7,E9,F,I,B,UP,C4) | clean |
| Byte-compile | `compileall` over app, package, eval, tests | clean |
| Unit tests | `unittest discover -s tests` | 101 passed, 0 skipped |
| Fresh-clone boot | import app, assert no document, assert empty-state copy | passes |
| Import surface | import app, backend, discovery against new venv | all import |
| Deprecated APIs | grep for `utcnow`, `typing.List`, `distutils`, legacy typing | none |
| Python 3.10 floor | `ruff check --select UP --target-version py310` | nothing to upgrade |
| Subprocess safety | discovery uses argv lists, never `shell=True` | confirmed |
| Secret hygiene | tracked files matching env/key/token/pdf/model patterns | only `.env.example` |
| Repo size | `du -sh .git` | 640K over 35 tracked files |
| Contributor set | `git shortlog -sne --all` | single identity |

## Dependencies reviewed

Kept, because they are reached indirectly and pinning them is deliberate:

- `pypdf` — PDF text extraction runs through
  `langchain_community.document_loaders.PyPDFLoader`, which needs it. Pinning
  holds the parser steady against a langchain-community bump.
- `transformers`, `sentence-transformers` — reached through
  `langchain_huggingface.HuggingFaceEmbeddings`. Their versions are coupled to
  gradio 6's dependency set, which is why `pyproject.toml` carries a
  `transformers>=4.57,<5` bound and `requirements.txt` pins them exactly.
- `deepeval` — evaluation only, already flagged as optional in the file.

## Naming

The project name is `MCP_Agentic_DocuChat` everywhere: 29 display-name
occurrences, zero stray casings. `agentic_docuchat` is the Python package and
`agentic-docuchat` the PyPI distribution name, which are fixed by naming rules
and deliberately differ in case and separators.

## Virtual environment convention

The environment directory is `venv`, not `avenv`. Documentation, the gitignore
and the local checkout all use `venv`, and the old `avenv` tree has been
removed. Rebuilt from `requirements.txt` from scratch to prove the documented
setup actually works.

## House style

Linting is **correctness only** (`E4,E7,E9,F,I,B,UP,C4`). The stylistic families
`SIM`, `RET` and `PERF` are deliberately excluded and are not enforced.

That is a decision, not an oversight. The `SIM115` findings are Chroma and
SQLite calls that cannot take a context manager, and the `PERF203` findings are
retry loops where the `try` block is the operation being retried. "Fixing" them
means restructuring working code to satisfy a linter, which is the kind of churn
that makes a codebase harder to read for no behavioural gain.

## Known limitations, not defects

- The smallest llama.cpp model produces weak and occasionally self-contradictory
  prose. That is model capacity, not application logic. Ollama `qwen3:1.7b`
  answers correctly on the same input.
- Ruff is installed as part of `requirements.txt` rather than a separate dev
  extra. The project has no dependency-group concept, and CI installs a single
  file, so this keeps one install path instead of introducing a second.