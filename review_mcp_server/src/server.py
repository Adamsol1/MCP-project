"""Review MCP Server — AI #2 review prompts for all intelligence phases.

This server is exclusively for the review agent (AI #2). It exposes review
prompt templates via the MCP Prompts primitive. ReviewService connects here
to fetch the appropriate review prompt for each phase, then calls LLMService
with that prompt.

Architecture:
  Port 8001 — Generation server (mcp_server/) — Agent #1 connects here
  Port 8002 — Review server (this file)        — Agent #2 connects here

This separation ensures Agent #1 cannot use review prompts and Agent #2
cannot accidentally call OSINT tools.
"""

import os
from sys import stderr

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.responses import JSONResponse

from prompts import register_prompts

load_dotenv()

print("Starting MCP Review Server...", file=stderr, flush=True)

mcp = FastMCP(
    name="ReviewServer",
    instructions=(
        "MCP server providing review prompt templates for AI #2. "
        "Each prompt instructs the reviewer how to evaluate output from a specific "
        "intelligence phase (Direction, Collection, Processing)."
    ),
)

register_prompts(mcp)


# ── Health check ─────────────────────────────────────────────────────────────

@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    print("Review server health check — running.", file=stderr, flush=True)
    return JSONResponse({"status": "ok", "server": "review"})


if __name__ == "__main__":
    port = int(os.getenv("REVIEW_MCP_PORT", "8002"))
    mcp.run(transport="sse", host="127.0.0.1", port=port, show_banner=False, log_level="INFO")
