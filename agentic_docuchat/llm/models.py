"""Which local models are sitting on this machine, right now?

Ollama and llama.cpp both say what they have over plain HTTP — this module
asks them and prints a friendly summary plus the exact `.env` lines that
select what it found. No API keys, no downloads, stdlib only.

Run:  python -m agentic_docuchat.llm.models
"""

from __future__ import annotations

import os
from typing import Any

from .llamacpp import llamacpp_status
from .ollama import ollama_status


def fetch_local_models(
    ollama_base_url: str | None = None,
    llamacpp_base_url: str | None = None,
) -> dict[str, Any]:
    """Probe both local providers; never raises, offline just means offline."""
    ollama_base_url = (ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).strip()
    llamacpp_base_url = (
        llamacpp_base_url or os.getenv("LLAMACPP_BASE_URL", "http://localhost:8080/v1")
    ).strip()
    ollama = ollama_status(ollama_base_url)
    llamacpp = llamacpp_status(llamacpp_base_url)
    return {
        "ollama": {"base_url": ollama_base_url, **ollama},
        "llamacpp": {"base_url": llamacpp_base_url, **llamacpp},
    }


def suggest_env(models: dict[str, Any]) -> list[str]:
    """`.env` lines selecting the first model found on each live provider."""
    lines: list[str] = []
    ollama_models = models["ollama"].get("models", []) if models["ollama"].get("running") else []
    llamacpp_models = (
        models["llamacpp"].get("models", []) if models["llamacpp"].get("running") else []
    )
    if ollama_models:
        lines.append(f"OLLAMA_MODEL={ollama_models[0]}")
    if llamacpp_models:
        lines.append(f"LLAMACPP_MODEL={llamacpp_models[0]}")
    return lines


def main() -> None:
    """Print what was found and the `.env` snippet to use it."""
    models = fetch_local_models()
    for provider in ("ollama", "llamacpp"):
        info = models[provider]
        if info["running"]:
            found = ", ".join(info["models"]) or "(server up, no models pulled yet)"
            print(f"{provider} ({info['base_url']}): running — {found}")
        else:
            print(f"{provider} ({info['base_url']}): offline")
    suggestions = suggest_env(models)
    if suggestions:
        print("\nSuggested .env:")
        for line in suggestions:
            print(f"  {line}")
    else:
        print(
            "\nNo local models found. Start something first:\n"
            "  ollama serve  →  ollama pull gemma3:4b\n"
            "  llama-server -hf Qwen/Qwen3-4B-GGUF:Q4_0 --port 8080"
        )


if __name__ == "__main__":
    main()
