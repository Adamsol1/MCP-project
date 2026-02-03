"""Tests for MCP client."""

import pytest

from src.mcp_client.client import MCPClient


class TestMCPClientInit:
    """Test MCP client initialization."""

    def test_client_stores_server_path(self) -> None:
        """Client should store the server script path."""
        client = MCPClient("/path/to/server.py")
        assert client.server_script_path == "/path/to/server.py"

    def test_client_session_initially_none(self) -> None:
        """Client session should be None before connecting."""
        client = MCPClient("/path/to/server.py")
        assert client.session is None


class TestMCPClientNotConnected:
    """Test MCP client behavior when not connected."""

    @pytest.mark.asyncio
    async def test_call_tool_raises_when_not_connected(self) -> None:
        """Calling a tool without connection should raise RuntimeError."""
        client = MCPClient("/path/to/server.py")

        with pytest.raises(RuntimeError, match="Not connected"):
            await client.call_tool("greet")

    @pytest.mark.asyncio
    async def test_list_tools_raises_when_not_connected(self) -> None:
        """Listing tools without connection should raise RuntimeError."""
        client = MCPClient("/path/to/server.py")

        with pytest.raises(RuntimeError, match="Not connected"):
            await client.list_tools()
