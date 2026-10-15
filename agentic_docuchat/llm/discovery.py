"""What local models already exist on disk — even when nothing is running.

A stopped Ollama server still has its pulled models, a stopped llama-server
still has the GGUFs it downloaded, and mlx-lm still has the MLX-quantised
repos in the Hugging Face cache. Those are exactly the models you want named
when the app says "offline" — otherwise the only advice left is "run
`ollama pull <name>`" with no idea which name you already have.

Each runtime already knows how to inventory itself, so we ask it rather than
guessing at its storage layout:

* ``ollama list``               — Ollama's own inventory (needs the daemon up)
* ``llama-server --cache-list`` — llama.cpp's cache, works with no server up
* ``mlx_lm.manage --scan``      — the MLX cache, works with no server up

Those are authoritative: they list exactly what the runtime can load. Where a
command is unavailable (not installed, too old, or its daemon is down) we fall
back to reading the known cache layout directly, so the offline case still
works.

Stdlib only. Nothing here raises: a machine with no local models, a missing
binary, a slow runtime, or a half-installed setup all return an empty list.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

# These are local filesystem/server queries; a hung runtime must not hang the UI.
_CLI_TIMEOUT_SECONDS = 8

# PATH can miss pipx and Homebrew directories when the app is launched from a
# GUI process (Finder, an IDE, a systemd unit) instead of a login shell.
_EXTRA_BIN_DIRS = (
    Path.home() / ".local" / "bin",
    Path("/opt/homebrew/bin"),
    Path("/usr/local/bin"),
)

# Where llama.cpp drops weights it fetches itself, and where people keep
# hand-downloaded GGUFs. LLAMACPP_MODEL_DIRS overrides the whole list.
DEFAULT_GGUF_DIRS = (
    "~/.cache/llama.cpp",
    "~/llama.cpp/models",
    "./models",
)

# `llama-server -hf org/repo:Q4_K_M` and `mlx_lm.server --model org/repo`
# both land in the Hugging Face hub cache as models--org--repo.
_HUB_REPO = re.compile(r"^models--(.+?)--(.+)$")

# Multi-part GGUFs: foo-00002-of-00003.gguf. llama-server loads shards by the
# first file's stem, so all three would otherwise show up as three models.
_SHARD_SUFFIX = re.compile(r"-\d{5}-of-\d{5}$")


# ------------------------------------------------------------------ invocation

def _which(*names: str) -> str | None:
    """First runnable binary among `names`, searched on PATH then known dirs."""
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    for directory in _EXTRA_BIN_DIRS:
        for name in names:
            candidate = directory / name
            try:
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    return str(candidate)
            except OSError:
                continue
    return None


def _run(argv: tuple[str, ...]) -> str:
    """stdout of `argv`, or "" if it is missing, slow, or unhappy.

    Never raises: discovery runs on the UI's status path, where an exception
    would take the app down over a listing command.
    """
    executable = _which(*argv)
    if executable is None:
        return ""
    try:
        done = subprocess.run(
            [executable, *argv[1:]],
            capture_output=True,
            text=True,
            timeout=_CLI_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout if done.returncode == 0 else ""


# ------------------------------------------------------------ Hugging Face cache

def _huggingface_hub_dirs() -> list[Path]:
    # HF_HOME relocates the whole cache rather than adding to it, so honour it
    # exclusively — scanning the default path as well would advertise models
    # that this machine's transformers/MLX would never look for.
    configured = os.getenv("HF_HOME", "").strip()
    candidates = (
        [Path(configured).expanduser() / "hub"]
        if configured
        else [Path.home() / ".cache" / "huggingface" / "hub"]
    )
    return [path for path in candidates if path.is_dir()]


def _hub_repos(*needles: str, weight_suffixes: tuple[str, ...] = ()) -> list[str]:
    """Cached HF repos whose id contains any needle, as ``org/repo``.

    Walking the hub one directory level at a time (rather than recursing into
    every model's blobs) is what keeps this cheap on a machine with tens of
    gigabytes of cached weights. ``weight_suffixes`` additionally requires the
    actual weight files to be present, so a half-finished download never gets
    offered as a model that would fail to load.
    """
    found: set[str] = set()
    for hub in _huggingface_hub_dirs():
        for repo in hub.glob("models--*"):
            match = _HUB_REPO.match(repo.name)
            if not match or not repo.is_dir():
                continue
            label = f"{match.group(1).replace('--', '/')}/{match.group(2)}"
            if not any(needle in label.lower() for needle in needles):
                continue
            if weight_suffixes and not _repo_has_weights(repo, weight_suffixes):
                continue
            found.add(label)
    return sorted(found)


def _repo_has_weights(repo: Path, suffixes: tuple[str, ...]) -> bool:
    """True only if the weights actually landed.

    Two traps this dodges: a repo that was merely *inspected* (mlx-lm reading
    a config leaves a snapshot with no weight file), and a download that was
    interrupted (a ``.downloadInProgress`` blob and no snapshot at all). Hub
    weight files are symlinks into ``blobs/``, so each candidate is resolved
    and required to have bytes behind it.
    """
    try:
        candidates = (path for path in repo.rglob("*") if path.suffix in suffixes)
        for path in candidates:
            try:
                if path.resolve().stat().st_size > 0:
                    return True
            except OSError:
                continue
    except OSError:
        return False
    return False


# -------------------------------------------------------------------- Ollama

def _ollama_manifest_tags() -> list[str]:
    """Tags read straight off disk, for when the daemon is not answering.

    Ollama stores one manifest file per tag and *the path is the tag*:
    ``<root>/registry.ollama.ai/library/gemma3/4b`` is the manifest for
    ``gemma3:4b``. Reading the layout instead of parsing manifest JSON keeps
    this working across Ollama versions.
    """
    base = Path(os.getenv("OLLAMA_HOME", "").strip() or Path.home() / ".ollama")
    root = base / "models" / "manifests"
    if not root.is_dir():
        return []
    found: set[str] = set()
    try:
        for manifest in (path for path in root.rglob("*") if path.is_file()):
            parts = manifest.relative_to(root).parts
            # <registry host> / <namespace…> / <model> / <tag>
            if len(parts) < 3 or manifest.name.startswith("."):
                continue
            tag, model, namespace = parts[-1], parts[-2], parts[1:-2]
            prefix = "/".join(namespace)
            found.add(f"{prefix}/{model}:{tag}" if prefix and prefix != "library" else f"{model}:{tag}")
    except OSError:
        pass
    return sorted(found)


def ollama_models_on_disk() -> list[str]:
    """Model tags Ollama has, e.g. ``['gemma3:1b', 'qwen3:1.7b']``.

    ``ollama list`` is authoritative but needs the daemon running, so the
    on-disk manifests cover the offline case.
    """
    listed = {
        line.split()[0]
        for line in _run(("ollama", "list")).splitlines()[1:]
        if line.split()
    }
    return sorted(listed or _ollama_manifest_tags())


# ------------------------------------------------------------ llama.cpp / MLX

def _scan_dirs(env_var: str, defaults: tuple[str, ...]) -> list[str]:
    """``*.gguf`` / weights found in explicitly configured model directories.

    These cover hand-placed files that never touch the Hugging Face cache.
    """
    configured = os.getenv(env_var, "").strip()
    raw = configured.split(os.pathsep) if configured else list(defaults)
    found: set[str] = set()
    for item in raw:
        directory = Path(item.strip()).expanduser()
        if not directory.is_dir():
            continue
        try:
            for path in sorted(directory.rglob("*.gguf")):
                found.add(str(path.with_name(_SHARD_SUFFIX.sub("", path.stem) + ".gguf")))
        except OSError:
            continue
    return sorted(found)


def _llamacpp_cache_entries() -> list[str]:
    """`llama-server --cache-list`, whose quant tags llama-server accepts verbatim.

    Output looks like::

        number of models in cache: 3
           1. ggml-org/SmolLM3-3B-GGUF:Q4_K_M
    """
    found = set()
    for line in _run(("llama-server", "--cache-list")).splitlines():
        match = re.match(r"\s*\d+\.\s+(\S+)", line)
        if match:
            found.add(match.group(1))
    return sorted(found)


def _mlx_cache_repos() -> list[str]:
    """`mlx_lm.manage --scan`, whose REPO ID column is directly loadable.

    The table is column-aligned, but padding depends on the widest repo id, so
    the gap between REPO ID and REPO TYPE is not reliably two spaces — the
    longest id has exactly one. Take the first whitespace-delimited token
    instead and accept it only if it looks like a repo id; a repo id never
    contains whitespace, so this is stable whatever the alignment.
    """
    found: set[str] = set()
    for line in _run(("mlx_lm.manage", "--scan")).splitlines():
        fields = line.split()
        if not fields:
            continue
        candidate = fields[0]
        # Skips the "REPO ID" header and the dashes beneath it.
        if "/" in candidate and not set(candidate) <= {"-"}:
            found.add(candidate)
    return sorted(found)


def gguf_models_on_disk() -> list[str]:
    """Local GGUFs as ``llama-server`` can serve them.

    The cache list comes first because it is what llama.cpp itself will load,
    quant tag included. Hand-placed files from ``LLAMACPP_MODEL_DIRS`` and the
    Hugging Face cache are merged in so a model you downloaded yourself but
    never served is still listed. Sharded files collapse to their shared stem.
    """
    entries = set(_llamacpp_cache_entries())
    entries |= set(_hub_repos("gguf", weight_suffixes=(".gguf",)))
    entries |= set(_scan_dirs("LLAMACPP_MODEL_DIRS", DEFAULT_GGUF_DIRS))
    # The cache names "org/repo:Q4_K_M" where the hub scan names "org/repo".
    # Keep the quant-specific entry (it is what llama.cpp actually cached and
    # what to feed back to -hf) and drop the bare duplicate.
    for entry in [e for e in entries if ":" in e]:
        entries.discard(entry.split(":", 1)[0])
    return sorted(entries)


def mlx_models_on_disk() -> list[str]:
    """Cached MLX repos ``mlx_lm.server --model`` can load.

    MLX models are ordinary Hugging Face repos carrying an ``mlx`` quantisation
    tag, so the cache scan is the fallback when ``mlx_lm.manage`` is missing.
    """
    return sorted(set(_mlx_cache_repos()) | set(_hub_repos("mlx", weight_suffixes=(".safetensors", ".npz"))))


# --------------------------------------------------------------------- hints

def _is_local_file(label: str) -> bool:
    """True when `label` is a file on this machine rather than a cache entry.

    ``llama-server -hf`` takes ``<user>/<model>[:quant]``. A hand-placed
    ``~/llama.cpp/models/foo.gguf`` has to be passed positionally instead, so
    the two forms cannot be handed to the same flag.
    """
    return label.endswith(".gguf") or label.startswith(("/", "./", "~", "../"))


def start_hint(provider: str) -> str:
    """The exact command that brings `provider` up, preferring what is on disk."""
    if provider == "ollama":
        return "ollama serve" if ollama_models_on_disk() else "ollama serve && ollama pull gemma3:4b"
    if provider == "llamacpp":
        on_disk = gguf_models_on_disk()
        if on_disk:
            # Prefer a cache entry (`-hf`); fall back to a local file, which
            # llama-server takes as a positional argument.
            for candidate in sorted(on_disk, key=_is_local_file):
                if _is_local_file(candidate):
                    return f'llama-server "{candidate}" --port 8080'
                return f"llama-server -hf {candidate} --port 8080"
        return "llama-server -hf Qwen/Qwen3-4B-GGUF:Q4_0 --port 8080"
    if provider == "mlx":
        on_disk = mlx_models_on_disk()
        if on_disk:
            return f"mlx_lm.server --model {on_disk[0]} --port 8081"
        return "mlx_lm.server --model mlx-community/gemma-3-4b-it-4bit --port 8081"
    return ""


def main() -> None:
    for provider, on_disk in (
        ("Ollama   ", ollama_models_on_disk()),
        ("llama.cpp", gguf_models_on_disk()),
        ("MLX     ", mlx_models_on_disk()),
    ):
        print(f"{provider} on disk: {', '.join(on_disk) or '(nothing yet)'}")
    print()
    for provider in ("ollama", "llamacpp", "mlx"):
        print(f"  start {provider:9} -> {start_hint(provider)}")


if __name__ == "__main__":
    main()
