"""MCP Threat Intelligence Server.

This server provides tools, resources, and prompts for the
Threat Intelligence workflow (Direction, Collection, Processing phases).
"""

from fastmcp import FastMCP

mcp = FastMCP(
    name="ThreatIntelligence",
    instructions="MCP server for Threat Intelligence workflow assistance.",
)


@mcp.tool
def greet() -> str:
    """Test tool to verify the server is running."""
    return "Hello, this is the MCP Threat Intelligence server!"


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
