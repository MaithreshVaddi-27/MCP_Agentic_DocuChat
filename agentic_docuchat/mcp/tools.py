"""MCP tool loading (Composio) — isolated here so the backend never imports
optional web-tool SDKs at module load. Everything stays lazy: unconfigured
or failing tools simply mean an empty list, never a crash.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("agentic_docuchat")


def load_mcp_tools(
    api_key: str | None, user_id: str | None, toolkits: list[str]
) -> list[Any]:
    """Fetch Composio toolkits for the agent; `[]` when unconfigured or on
    any error (no keys, no network, unknown toolkit)."""
    if not (api_key and user_id and toolkits):
        return []
    try:
        from composio import Composio
        from composio_langchain import LangchainProvider

        composio = Composio(api_key=api_key, provider=LangchainProvider())
        tools = composio.tools.get(user_id=user_id, toolkits=toolkits)
        logger.info(
            "Loaded %s Composio tool(s) from toolkits: %s", len(tools), ", ".join(toolkits)
        )
        return tools
    except Exception as error:
        logger.warning("Composio tools disabled (%s): %s", ", ".join(toolkits), error)
        return []
