"""MCP Threat Intelligence Server.

This server provides tools, resources, and prompts for the
Threat Intelligence workflow (Direction, Collection, Processing phases).
"""

import os

from dotenv import load_dotenv
from fastmcp import FastMCP
from google import genai

load_dotenv()

print("Starting MCP Threat Intelligence Server...", flush=True)

api_key = os.getenv("GEMINI_API_KEY")
print(f"API KEY FOUND: {bool(api_key)}", flush=True)

client = genai.Client(api_key=api_key)

mcp = FastMCP(
    name="ThreatIntelligence",
    instructions="MCP server for Threat Intelligence workflow assistance.",
)


@mcp.tool
def greet() -> str:
    """Test tool to verify the server is running."""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Say hello, say what model you are, and mentiond todays' date if you can. Also answer 2+2",
    )

    return f"Hello, this is the MCP Threat Intelligence server! Gemini Response: {response.text}"


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
