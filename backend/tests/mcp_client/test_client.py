"""Tests for MCP client."""

import pytest
from mcp.types import TextContent

from src.mcp_client.client import MCPClient
from src.models.dialogue import DialogueContext


class TestMCPClientInit:
    """Test MCP client initialization."""

    def test_client_stores_server_path(self) -> None:
        """Client should store the configured server URL."""
        client = MCPClient("http://127.0.0.1:9999/sse")
        assert client.server_url == "http://127.0.0.1:9999/sse"

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
        # Struktur matcher ekte MCP SDK-resultat: result.content[0].text
        class MockSession:
            async def call_tool(self, tool_name, arguments):  # noqa: ARG002
                class MCPResult:
                    content = [
                        TextContent(
                            type="text",
                            text="Generated PIR: Investigate APT29 targeting Norway",
                        )
                    ]

                return MCPResult()

        # Sett fake session på klienten
        client.session = MockSession()  # type: ignore

        # test data for dialoguecontext
        context = DialogueContext()
        context.scope = "identify attack patterns"
        context.timeframe = "last 6 months"
        context.target_entities = ["Norway"]

        # Kall på generer PIR
        result = await client.call_tool(
            "generate_pir",
            {
                "scope": context.scope,
                "timeframe": context.timeframe,
                "target_entities": context.target_entities,
                "perspectives": ["neutral"],
            },
        )

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
            await client.call_tool(
                "generate_pir",
                {
                    "scope": context.scope,
                    "timeframe": context.timeframe,
                    "target_entities": context.target_entities,
                    "perspectives": ["neutral"],
                },
            )


class TestMCPClientStripFences:
    """Tests for the _strip_fences helper that removes markdown code fences
    Gemini occasionally wraps its JSON output in.

    _strip_fences should:
      - Remove ```json ... ``` wrappers
      - Remove ``` ... ``` wrappers (no language tag)
      - Leave plain text completely unchanged
    """

    def test_plain_json_string_is_unchanged(self) -> None:
        """A raw JSON string without fences must pass through untouched."""
        raw = '{"summary": "some text"}'
        assert MCPClient._strip_fences(raw) == raw

    def test_strips_json_language_fence(self) -> None:
        """```json ... ``` wrapper should be removed, leaving only the JSON."""
        fenced = '```json\n{"summary": "some text"}\n```'
        assert MCPClient._strip_fences(fenced) == '{"summary": "some text"}'

    def test_strips_generic_fence_no_language_tag(self) -> None:
        """``` ... ``` wrapper (no language tag) should also be stripped."""
        fenced = '```\n{"result": "data"}\n```'
        assert MCPClient._strip_fences(fenced) == '{"result": "data"}'

    def test_plain_text_is_unchanged(self) -> None:
        """Non-JSON plain text without fences must pass through untouched."""
        raw = "Generated PIR: Investigate APT29 targeting Norway"
        assert MCPClient._strip_fences(raw) == raw

    def test_strips_fences_with_leading_and_trailing_whitespace(self) -> None:
        """Surrounding whitespace/newlines outside the fences should be ignored."""
        fenced = '  \n```json\n{"key": "value"}\n```\n  '
        assert MCPClient._strip_fences(fenced) == '{"key": "value"}'

    def test_multiline_json_inside_fence_is_preserved(self) -> None:
        """Newlines inside the JSON body must not be stripped."""
        inner = '{\n  "pirs": [\n    {"question": "Q1"}\n  ]\n}'
        fenced = f"```json\n{inner}\n```"
        assert MCPClient._strip_fences(fenced) == inner


class TestMCPClientCallToolParsing:
    """Tests that call_tool correctly parses the text returned by the MCP server,
    including responses where Gemini has wrapped the JSON in markdown fences.
    """

    def _make_client_with_response(self, response_text: str) -> MCPClient:
        """Helper: returns an MCPClient whose mock session returns response_text."""
        client = MCPClient("/fake/path/server.py")

        class MockSession:
            async def call_tool(self, tool_name, arguments):  # noqa: ARG002
                class MCPResult:
                    content = [TextContent(type="text", text=response_text)]

                return MCPResult()

        client.session = MockSession()  # type: ignore
        return client

    @pytest.mark.asyncio
    async def test_plain_json_response_is_parsed_to_dict(self) -> None:
        """A plain JSON response (no fences) should be returned as a dict."""
        client = self._make_client_with_response('{"summary": "some text"}')
        result = await client.call_tool("generate_summary", {})
        assert result == {"summary": "some text"}

    @pytest.mark.asyncio
    async def test_fenced_json_response_is_parsed_to_dict(self) -> None:
        """A ```json fenced response should have fences stripped and be parsed to a dict."""
        client = self._make_client_with_response(
            '```json\n{"summary": "some text"}\n```'
        )
        result = await client.call_tool("generate_summary", {})
        assert result == {"summary": "some text"}

    @pytest.mark.asyncio
    async def test_generic_fenced_json_response_is_parsed_to_dict(self) -> None:
        """A generic ``` fenced response should have fences stripped and be parsed to a dict."""
        client = self._make_client_with_response('```\n{"summary": "some text"}\n```')
        result = await client.call_tool("generate_summary", {})
        assert result == {"summary": "some text"}

    @pytest.mark.asyncio
    async def test_plain_text_response_is_returned_as_string(self) -> None:
        """A response that is not JSON should be returned as a plain string."""
        client = self._make_client_with_response("Hello from the server")
        result = await client.call_tool("greet", {})
        assert result == "Hello from the server"
