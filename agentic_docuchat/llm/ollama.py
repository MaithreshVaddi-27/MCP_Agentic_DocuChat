"""Small, friendly health checks: is Ollama awake, and is there a GPU?

Never installs or starts anything — just peeks (a quick HTTP ping, and
`nvidia-smi` / macOS system info if present) so the status panel can show
an honest green or red dot.
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen



def _command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def detect_gpu() -> dict[str, Any]:
    if _command_exists("nvidia-smi"):
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return {"available": True, "kind": "NVIDIA", "details": result.stdout.strip()}
        except (OSError, subprocess.SubprocessError):
            pass
    if platform.system() == "Darwin" and _command_exists("system_profiler"):
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return {"available": True, "kind": "Apple GPU", "details": "Detected by macOS"}
        except (OSError, subprocess.SubprocessError):
            pass
    return {"available": False, "kind": "CPU", "details": "No supported GPU detected"}


def ollama_status(base_url: str = "http://localhost:11434") -> dict[str, Any]:
    status: dict[str, Any] = {
        "installed": _command_exists("ollama"),
        "running": False,
        "models": [],
        "gpu": detect_gpu(),
    }
    try:
        request = Request(f"{base_url.rstrip('/')}/api/tags", method="GET")
        with urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        status["running"] = True
        status["models"] = [item.get("name", "") for item in payload.get("models", [])]
    except (OSError, URLError, ValueError):
        pass
    return status
