"""Small, friendly health check: is your local llama.cpp server awake?

Just pings `llama-server`'s `/v1/models` endpoint (the OpenAI-compatible
server that ships with llama.cpp), e.g. started with:

    llama-server -hf Qwen/Qwen3-4B-GGUF:Q4_0 --port 8080

which serves at http://localhost:8080/v1.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from .discovery import gguf_models_on_disk


def llamacpp_status(base_url: str = "http://localhost:8080/v1", timeout: float = 2.0) -> dict[str, Any]:
    """Ping the llama.cpp server's /v1/models endpoint.

    Returns a dict shaped like the one llm.ollama.ollama_status() returns
    so the rest of the app (status panel, error messages) can treat every
    local provider the same way. ``models_on_disk`` reports GGUFs that are
    ready to serve even while the server is stopped.
    """
    status: dict[str, Any] = {
        "running": False,
        "models": [],
        "models_on_disk": gguf_models_on_disk(),
    }
    url = f"{base_url.rstrip('/')}/models"
    try:
        request = Request(url, method="GET")
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        status["running"] = True
        status["models"] = [item.get("id", "") for item in payload.get("data", [])]
    except (OSError, URLError, ValueError):
        pass
    return status
