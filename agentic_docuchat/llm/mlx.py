"""Small, friendly health check: is your local MLX server awake?

Just pings `mlx_lm.server`'s `/v1/models` endpoint (the OpenAI-compatible
server that ships with mlx-lm, handy on Apple Silicon), e.g. started with:

    mlx_lm.server --model mlx-community/gemma-3-4b-it-4bit --port 8081

which serves at http://localhost:8081/v1.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


def mlx_status(base_url: str = "http://localhost:8081/v1", timeout: float = 2.0) -> dict[str, Any]:
    """Ping the MLX server's /v1/models endpoint.

    Returns a dict shaped like the one ollama_utils.ollama_status() returns
    so the rest of the app (status panel, error messages) can treat every
    local provider the same way.
    """
    status: dict[str, Any] = {"running": False, "models": []}
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
