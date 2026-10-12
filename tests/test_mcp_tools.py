import unittest

from agentic_docuchat.mcp.tools import load_mcp_tools


class McpToolsTests(unittest.TestCase):
    """MCP loading must fail closed: unconfigured or broken tooling is an
    empty toolbox, never an exception at startup or question time."""

    def test_unconfigured_returns_empty(self):
        self.assertEqual(load_mcp_tools(None, None, ["TAVILY"]), [])
        self.assertEqual(load_mcp_tools("key", "", ["TAVILY"]), [])
        self.assertEqual(load_mcp_tools("key", "user", []), [])

    def test_broken_sdk_import_fails_closed(self):
        import sys
        from unittest import mock

        with mock.patch.dict(sys.modules, {"composio": None, "composio_langchain": None}):
            self.assertEqual(load_mcp_tools("key", "user", ["TAVILY"]), [])


if __name__ == "__main__":
    unittest.main()
