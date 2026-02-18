"""MCP Client for connecting to the Threat Intelligence MCP Server."""

import asyncio
import sys
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..models.dialogue import DialogueContext


class MCPClient:
    """Client for communicating with the MCP Threat Intelligence server."""

    def __init__(self, server_script_path: str) -> None:
        """Initialize the MCP client.

        Args:
            server_script_path: Path to the MCP server script (server.py).
        """
        self.server_script_path = server_script_path
        self.session: ClientSession | None = None

    @asynccontextmanager
    async def connect(self):
        """Connect to the MCP server.

        Yields:
            The connected client instance.
        """
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[self.server_script_path],
        )

        async with (
            stdio_client(server_params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            self.session = session
            yield self

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> Any:
        """Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call.
            arguments: Arguments to pass to the tool.

        Returns:
            The tool's response.

        Raises:
            RuntimeError: If not connected to the server.
        """
        if not self.session:
            raise RuntimeError(
                "Not connected to MCP server. Use 'async with client.connect():'"
            )

        result = await self.session.call_tool(tool_name, arguments or {})
        return result

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools on the MCP server.

        Returns:
            List of available tools with their metadata.

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


async def main() -> None:
    """Example usage of the MCP client."""
    from pathlib import Path

    # Get path to server script
    project_root = Path(__file__).parent.parent.parent.parent
    server_path = project_root / "mcp_server" / "src" / "server.py"

    if not server_path.exists():
        print(f"Server not found at: {server_path}")
        sys.exit(1)

    client = MCPClient(str(server_path))

    async with client.connect():
        # List available tools
        tools = await client.list_tools()
        print("Available tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")

        # Call the greet tool
        result = await client.call_tool("greet")
        print(f"\nGreet result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
