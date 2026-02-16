"""Tests for MCP client."""

import pytest

from src.mcp_client.client import MCPClient
from src.models.dialogue import DialogueContext


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


class TestMCPClientTools:
    @pytest.mark.asyncio
    async def test_generate_PIR_returns_result(self):
        # Lag en mock MCPClient
        client = MCPClient("/fake/path/server.py")

        # Lag en fake session som returnerer et svar
        class MockSession:
            async def call_tool(self, tool_name, arguments):  # noqa: ARG002
                return "Generated PIR: Investigate APT29 targeting Norway"

        # Sett fake session på klienten
        client.session = MockSession()  # type: ignore

        # test data for dialoguecontext
        context = DialogueContext()
        context.scope = "identify attack patterns"
        context.timeframe = "last 6 months"
        context.target_entities = ["Norway"]

        # Kall på generer PIR
        result = await client.call_tool("generate_pir", {
                    "scope": context.scope,
                    "timeframe": context.timeframe,
                    "target_entities": context.target_entities,
                    "perspectives": ["neutral"],
        })

        # Sjekk return verdi
        assert result == "Generated PIR: Investigate APT29 targeting Norway"

    @pytest.mark.asyncio
    async def test_call_tool_generate_pir_raises_when_not_connected(self) -> None:
        """Calling a tool without connection should raise RuntimeError."""
        client = MCPClient("/path/to/server.py")

        # Create test data for test
        context = DialogueContext()
        context.scope = "identify attack patterns"
        context.timeframe = "last 6 months"
        context.target_entities = ["Norway"]

        with pytest.raises(RuntimeError, match="Not connected"):
            await client.call_tool("generate_pir", {
                "scope": context.scope,
                "timeframe": context.timeframe,
                "target_entities": context.target_entities,
                "perspectives": ["neutral"],
            })





