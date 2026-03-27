"""MCP Threat Intelligence Server - Generation Server (port 8001)."""

import os
from sys import stderr

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.responses import JSONResponse

from prompts import register_prompts
from tools.google_search import register_google_search_tools
from tools.knowledge_tools import register_knowledge_resources, register_knowledge_tools
from tools.local_search import register_local_search_tools
from tools.otx_tools import register_otx_tools
from tools.upload_tools import register_upload_tools

load_dotenv()

print("Starting MCP Threat Intelligence Server...", file=stderr, flush=True)

mcp = FastMCP(
    name="ThreatIntelligence",
    instructions=(
        "MCP server providing OSINT tools and knowledge bank resources for the "
        "Collection and Processing phases of the Threat Intelligence cycle."
    ),
)

# Tools and resources registration
register_knowledge_resources(mcp)
register_knowledge_tools(mcp)
register_upload_tools(mcp)
register_google_search_tools(mcp)
register_otx_tools(mcp)
register_local_search_tools(mcp)
register_prompts(mcp)


# Health check
@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    print("Health check - server is running.", file=stderr, flush=True)
    return JSONResponse({"status": "ok"})


# Test tool


@mcp.tool
def greet() -> str:
    """Test tool to verify the server is running."""
    print("MCP greet() called - server is running.", file=stderr, flush=True)
    return "MCP Threat Intelligence Server is running."


if __name__ == "__main__":
    port = int(os.getenv("MCP_SERVER_PORT", "8001"))
    mcp.run(
        transport="sse",
        host="127.0.0.1",
        port=port,
        show_banner=False,
        log_level="INFO",
    )
