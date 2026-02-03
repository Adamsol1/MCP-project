"""Tests for MCP server initialization."""

import pytest

from src.server import greet, mcp


class TestServerInitialization:
    """Test that the MCP server initializes correctly."""

    def test_server_has_correct_name(self) -> None:
        """Server should be named ThreatIntelligence."""
        assert mcp.name == "ThreatIntelligence"

    def test_greet_tool_returns_message(self) -> None:
        """Greet tool should return expected message."""
        result = greet()
        assert result == "Hello, this is the MCP Threat Intelligence server!"

    def test_greet_tool_registered(self) -> None:
        """Greet tool should be registered with the server."""
        tool_names = [tool.name for tool in mcp._tool_manager.tools.values()]
        assert "greet" in tool_names
