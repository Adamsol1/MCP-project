"""MCP Client — connects to the standalone MCP server via SSE/HTTP.

The MCP server runs as a separate process (started independently via
`python mcp_server/src/server.py`). This client connects to it over HTTP
using Server-Sent Events (SSE) transport — no subprocess management needed.
"""

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.types import TextContent

logger = logging.getLogger("app")

_DEFAULT_URL = "http://127.0.0.1:8001/sse"


class MCPClient:
    """Client for communicating with the MCP Threat Intelligence server.

    Connects to a running MCP server via SSE (HTTP). The server must be
    started separately before calling connect().

    Args:
        server_url: SSE endpoint URL of the running MCP server.
                    Defaults to the MCP_SERVER_URL env var, or
                    http://127.0.0.1:8001/sse if unset.
    """

    def __init__(self, server_url: str | None = None) -> None:
        self.server_url = server_url or os.getenv("MCP_SERVER_URL", _DEFAULT_URL)
        self.session: ClientSession | None = None

    @asynccontextmanager
    async def connect(self):
        """Connect to the running MCP server.

        Yields:
            The connected client instance.

        Raises:
            httpx.ConnectError: If the MCP server is not running at server_url.
        """
        logger.info(f"[MCP] Connecting to {self.server_url}...")
        async with (
            sse_client(self.server_url) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            self.session = session
            logger.info("[MCP] Connected")
            yield self
        self.session = None
        logger.info("[MCP] Disconnected")

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
            List of dicts with 'name' and 'description' keys.

        Raises:
            RuntimeError: If not connected to the server.
        """
        if not self.session:
            raise RuntimeError(
                "Not connected to MCP server. Use 'async with client.connect():'"
            )

        result = await self.session.list_tools()
        return [
            {"name": tool.name, "description": tool.description}
            for tool in result.tools
        ]

    @staticmethod
    def _strip_fences(text: str) -> str:
        """Strip markdown code fences (``` ... ```) from text."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            return "\n".join(lines[1:-1])
        return text
