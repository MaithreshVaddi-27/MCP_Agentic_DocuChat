"""Which local models are sitting on this machine, right now?

Ollama, llama.cpp, and MLX all say what they have over plain HTTP — this
module asks them and prints a friendly summary plus the exact `.env` lines
that select what it found. No API keys, no downloads, stdlib only.

Run:  python -m agentic_docuchat.llm.models
"""

from __future__ import annotations

import os
from typing import Any

from .discovery import start_hint
from .llamacpp import llamacpp_status
from .mlx import mlx_status
from .ollama import ollama_status


def fetch_local_models(
    ollama_base_url: str | None = None,
    llamacpp_base_url: str | None = None,
    mlx_base_url: str | None = None,
) -> dict[str, Any]:
    """Probe all local providers; never raises, offline just means offline."""
    ollama_base_url = (ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).strip()
    llamacpp_base_url = (
        llamacpp_base_url or os.getenv("LLAMACPP_BASE_URL", "http://localhost:8080/v1")
    ).strip()
    mlx_base_url = (
        mlx_base_url or os.getenv("MLX_BASE_URL", "http://localhost:8081/v1")
    ).strip()
    ollama = ollama_status(ollama_base_url)
    llamacpp = llamacpp_status(llamacpp_base_url)
    mlx = mlx_status(mlx_base_url)
    return {
        "ollama": {"base_url": ollama_base_url, **ollama},
        "llamacpp": {"base_url": llamacpp_base_url, **llamacpp},
        "mlx": {"base_url": mlx_base_url, **mlx},
    }


def suggest_env(models: dict[str, Any]) -> list[str]:
    """`.env` lines selecting the first model found on each live provider."""
    lines: list[str] = []
    ollama_models = models["ollama"].get("models", []) if models["ollama"].get("running") else []
    llamacpp_models = (
        models["llamacpp"].get("models", []) if models["llamacpp"].get("running") else []
    )
    mlx_models = models.get("mlx", {}).get("models", []) if models.get("mlx", {}).get("running") else []
    if ollama_models:
        lines.append(f"OLLAMA_MODEL={ollama_models[0]}")
    if llamacpp_models:
        lines.append(f"LLAMACPP_MODEL={llamacpp_models[0]}")
    if mlx_models:
        lines.append(f"MLX_MODEL={mlx_models[0]}")
    return lines


def _describe(provider: str, info: dict[str, Any]) -> str:
    """One status line: live server if up, otherwise what is waiting on disk."""
    if info["running"]:
        served = ", ".join(info["models"]) or "(server up, no models loaded)"
        return f"{provider} ({info['base_url']}): running — {served}"
    on_disk = info.get("models_on_disk") or []
    if on_disk:
        found = ", ".join(on_disk[:4]) + (f" (+{len(on_disk) - 4} more)" if len(on_disk) > 4 else "")
        return (
            f"{provider} ({info['base_url']}): offline — {len(on_disk)} model(s) already on disk: {found}"
        )
    return f"{provider} ({info['base_url']}): offline — nothing on disk yet"


def main() -> None:
    """Print what was found and the `.env` snippet to use it."""
    models = fetch_local_models()
    for provider in ("ollama", "llamacpp", "mlx"):
        print(_describe(provider, models[provider]))

    suggestions = suggest_env(models)
    if suggestions:
        print("\nSuggested .env:")
        for line in suggestions:
            print(f"  {line}")
        return

    print("\nNo provider is serving right now. Start one:")
    for provider in ("ollama", "llamacpp", "mlx"):
        print(f"  {start_hint(provider)}")


if __name__ == "__main__":
    main()
