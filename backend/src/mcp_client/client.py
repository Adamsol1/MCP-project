"""MCP Client — connects to the standalone MCP server via SSE/HTTP.

The MCP server runs as a separate process (started independently via
`python mcp_server/src/server.py`). This client connects to it over HTTP
using Server-Sent Events (SSE) transport — no subprocess management needed.
"""

import json
import logging
import os
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.types import ElicitResult, TextContent
from pydantic import AnyUrl

logger = logging.getLogger("app")

_DEFAULT_URL = "http://127.0.0.1:8001/sse"

# Receives (message, options) from the MCP server and returns the chosen option.
ElicitationCallback = Callable[[str, list[str]], Awaitable[str]]

_RESTRICTED_TLP = frozenset({"TLP:RED", "TLP:AMBER", "TLP:AMBER+STRICT"})
_USE_LOCAL = "Bytt til lokal LLM"
_USE_CLOUD = "Fortsett med Gemini"


def _get_tlp_level(content_header: str) -> str | None:
    upper = content_header.upper()
    for level in ("TLP:RED", "TLP:AMBER+STRICT", "TLP:AMBER", "TLP:GREEN", "TLP:CLEAR"):
        if level in upper:
            return level
    return None


class MCPClient:
    """Client for communicating with the MCP Threat Intelligence server.

    Connects to a running MCP server via SSE (HTTP). The server must be
    started separately before calling connect().

    Args:
        server_url:           SSE endpoint URL of the running MCP server.
                              Defaults to the MCP_SERVER_URL env var, or
                              http://127.0.0.1:8001/sse if unset.
        elicitation_callback: Optional async function invoked when the MCP server
                              sends an elicitation/create request mid-tool-call.
                              Receives (message, options) and must return the
                              chosen option string. When None, elicitation
                              requests are silently declined by the SDK.
    """

    def __init__(
        self,
        server_url: str | None = None,
        elicitation_callback: ElicitationCallback | None = None,
    ) -> None:
        self.server_url = server_url or os.getenv("MCP_SERVER_URL", _DEFAULT_URL)
        self.session: ClientSession | None = None
        self._elicitation_callback = elicitation_callback
        self._resource_tlp_warned: bool = False

    @asynccontextmanager
    async def connect(self):
        """Connect to the running MCP server.

        Yields:
            The connected client instance.

        Raises:
            httpx.ConnectError: If the MCP server is not running at server_url.
        """
        logger.info(f"[MCP] Connecting to {self.server_url}...")

        sdk_callback = None
        if self._elicitation_callback:
            sdk_callback = self._make_sdk_callback(self._elicitation_callback)

        async with (
            sse_client(self.server_url) as (read, write),
            ClientSession(read, write, elicitation_callback=sdk_callback) as session,
        ):
            await session.initialize()
            self.session = session
            logger.info("[MCP] Connected")
            yield self
        self.session = None
        logger.info("[MCP] Disconnected")

    @staticmethod
    def _make_sdk_callback(user_callback: ElicitationCallback):
        """Wrap our simple (message, options) → str callback in the SDK's expected signature.

        The SDK passes a full ElicitRequest object and expects an ElicitResult back.
        We extract the message and any enum options from the schema, call the user
        callback, then wrap the answer in an ElicitResult.
        """
        async def _sdk_elicitation_callback(ctx, params, /):
            message = params.message

            # Extract options from requestedSchema (camelCase, plain dict).
            # FastMCP encodes list[str] response_type as a string property named
            # "value" with an enum list.
            options: list[str] = []
            schema: dict = getattr(params, "requestedSchema", None) or {}
            for prop in schema.get("properties", {}).values():
                if isinstance(prop, dict) and prop.get("enum"):
                    options = [str(v) for v in prop["enum"]]
                    break
            chosen = await user_callback(message, options)
            return ElicitResult(action="accept", content={"value": chosen})

        return _sdk_elicitation_callback

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> Any:
        """Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call.
            arguments: Arguments to pass to the tool.

        Returns:
            Parsed JSON dict if the response is valid JSON, otherwise raw string.

        Raises:
            RuntimeError: If not connected to the server.
        """
        if not self.session:
            raise RuntimeError(
                "Not connected to MCP server. Use 'async with client.connect():'"
            )

        logger.info(f"[MCP] Calling tool: {tool_name}")
        start = time.time()
        try:
            result = await self.session.call_tool(tool_name, arguments or {})
        except Exception as e:
            logger.error(
                f"[MCP] Tool {tool_name} failed in {time.time() - start:.2f}s: {type(e).__name__}: {e}"
            )
            raise
        logger.info(f"[MCP] Tool {tool_name} completed in {time.time() - start:.2f}s")

        if not result.content:
            raise ValueError(f"MCP tool '{tool_name}' returned empty content")
        content_item = result.content[0]
        if not isinstance(content_item, TextContent):
            raise ValueError(f"Unexpected content type: {type(content_item).__name__}")
        text = content_item.text

        try:
            return json.loads(self._strip_fences(text))
        except json.JSONDecodeError:
            return text

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools on the MCP server.

        Returns:
            List of dicts with 'name', 'description', and 'inputSchema' keys.
            inputSchema follows JSON Schema format and describes the tool's parameters.

        Raises:
            RuntimeError: If not connected to the server.
        """
        if not self.session:
            raise RuntimeError(
                "Not connected to MCP server. Use 'async with client.connect():'"
            )

        result = await self.session.list_tools()

        def _schema(s):
            if s is None:
                return {}
            if isinstance(s, dict):
                return s
            return s.model_dump()

        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": _schema(tool.inputSchema),
            }
            for tool in result.tools
        ]

    async def get_prompt(
        self, name: str, arguments: dict[str, str] | None = None
    ) -> str:
        """Fetch a rendered prompt template from the MCP server.

        Args:
            name: Registered prompt name, e.g. "direction_gathering".
            arguments: Key-value arguments to fill into the template.
                       All values must be strings per the MCP Prompts spec.

        Returns:
            The rendered prompt text, ready to send to an LLM.

        Raises:
            RuntimeError: If not connected to the server.
        """
        if not self.session:
            raise RuntimeError(
                "Not connected to MCP server. Use 'async with client.connect():'"
            )

        logger.info(f"[MCP] Fetching prompt: {name}")
        result = await self.session.get_prompt(name, arguments or {})
        return "\n".join(
            msg.content.text for msg in result.messages if hasattr(msg.content, "text")
        )

    async def list_resources(self) -> list[dict[str, Any]]:
        """List available resources on the MCP server.

        Returns:
            List of dicts with 'uri', 'name', 'description', and 'mimeType' keys.

        Raises:
            RuntimeError: If not connected to the server.
        """
        if not self.session:
            raise RuntimeError(
                "Not connected to MCP server. Use 'async with client.connect():'"
            )

        result = await self.session.list_resources()
        return [
            {
                "uri": str(resource.uri),
                "name": resource.name,
                "description": resource.description,
                "mimeType": getattr(resource, "mimeType", None),
            }
            for resource in result.resources
        ]

    async def _maybe_elicit_classified(self, content: str) -> bool:
        """Check content header for restricted TLP and elicit provider-switch if needed.

        Host-driven counterpart to _maybe_elicit_provider_switch() in the MCP server.
        Called from read_resource() when the backend proactively fetches knowledge.
        Fires at most once per MCPClient instance (one per request/session).

        Returns True if the content should be blocked (user chose local LLM).
        """
        if not self._elicitation_callback or self._resource_tlp_warned:
            return False

        tlp = _get_tlp_level(content[:300])
        if tlp not in _RESTRICTED_TLP:
            return False

        choice = await self._elicitation_callback(
            f"Klassifisert innhold oppdaget ({tlp}). "
            f"Du kjører Gemini (sky-LLM). Klassifiserte ressurser bør ikke sendes til en sky-LLM. "
            f"Vil du bytte til lokal LLM?",
            [_USE_LOCAL, _USE_CLOUD],
        )
        self._resource_tlp_warned = True
        return choice == _USE_LOCAL

    async def read_resource(self, uri: str) -> str:
        """Read a resource by URI from the MCP server.

        Args:
            uri: The resource URI, e.g. "knowledge://geopolitical/norway_russia"
                 or "knowledge://index".

        Returns:
            The text content of the resource.

        Raises:
            RuntimeError: If not connected to the server.
            ValueError: If the resource has no text content.
        """
        if not self.session:
            raise RuntimeError(
                "Not connected to MCP server. Use 'async with client.connect():'"
            )

        logger.info(f"[MCP] Reading resource: {uri}")
        start = time.time()
        try:
            result = await self.session.read_resource(AnyUrl(uri))
        except Exception as e:
            logger.error(
                f"[MCP] Resource {uri} failed in {time.time() - start:.2f}s: {type(e).__name__}: {e}"
            )
            raise
        logger.info(f"[MCP] Resource {uri} read in {time.time() - start:.2f}s")

        for content_item in result.contents:
            if hasattr(content_item, "text"):
                content = content_item.text
                blocked = await self._maybe_elicit_classified(content)
                if blocked:
                    logger.info(f"[MCP] Resource {uri} blocked — user chose local LLM")
                    return ""
                return content
        raise ValueError(f"No text content in resource: {uri}")

    @staticmethod
    def _strip_fences(text: str) -> str:
        """Strip markdown code fences (``` ... ```) from text."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            return "\n".join(lines[1:-1])
        return text
