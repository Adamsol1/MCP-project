"""Review MCP Server — AI #2 review prompts for all intelligence phases.

This server is exclusively for the review agent (AI #2). It exposes review
prompt templates via the MCP Prompts primitive. ReviewService connects here
to fetch the appropriate review prompt for each phase, then calls LLMService
(Gemini) with that prompt.

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

from prompts import (
    build_collection_review_prompt,
    build_direction_review_prompt,
)

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


# ── Review Prompts ────────────────────────────────────────────────────────────

@mcp.prompt
def direction_review(content: str, context: str) -> str:
    """Review prompt for PIRs generated in the Direction phase.

    Args:
        content: The generated PIRs to review (JSON string).
        context: The dialogue context used to generate the PIRs (JSON string).
    """
    print("[ReviewServer] direction_review prompt requested", file=stderr, flush=True)
    return build_direction_review_prompt(content, context)


@mcp.prompt
def collection_review(content: str, context: str) -> str:
    """Review prompt for data collected in the Collection phase.

    Args:
        content: The collected data summary to review (JSON string).
        context: The collection plan and PIRs used as basis (JSON string).
    """
    print("[ReviewServer] collection_review prompt requested", file=stderr, flush=True)
    return build_collection_review_prompt(content, context)


@mcp.prompt
def processing_review(content: str, context: str) -> str:
    """Review prompt for correlations produced in the Processing phase.

    Args:
        content: The correlation report to review (JSON string).
        context: The collected data used as input (JSON string).
    """
    print("[ReviewServer] processing_review prompt requested", file=stderr, flush=True)
    return build_processing_review_prompt(content, context)


# ── Health check ─────────────────────────────────────────────────────────────

@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    print("Review server health check — running.", file=stderr, flush=True)
    return JSONResponse({"status": "ok", "server": "review"})


if __name__ == "__main__":
    port = int(os.getenv("REVIEW_MCP_PORT", "8002"))
    mcp.run(transport="sse", host="127.0.0.1", port=port, show_banner=False, log_level="INFO")
