"""MCP Threat Intelligence Server.

This server provides Tools and Resources for the Collection and Processing
phases of the Threat Intelligence workflow. The AI agent (GeminiAgent) running
in the backend calls these tools directly via the MCP protocol.

Direction phase does NOT use this server — all Direction AI calls go through
LLMService directly in the backend. See plan.md Architectural Design Decisions.
"""

import json
from pathlib import Path
from sys import stderr

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.responses import JSONResponse

from resources import KNOWLEDGE_REGISTRY, RESOURCES_DIR

load_dotenv()

print("Starting MCP Threat Intelligence Server...", file=stderr, flush=True)

mcp = FastMCP(
    name="ThreatIntelligence",
    instructions="MCP server providing OSINT tools and knowledge bank resources for the Collection and Processing phases of the Threat Intelligence cycle.",
)


# ── Knowledge Bank ────────────────────────────────────────────────────────────

@mcp.tool
def list_knowledge_base() -> str:
    """List all available knowledge bank resource IDs.

    Returns a JSON array of resource IDs the agent can read with read_knowledge_base().
    Call this first to discover what knowledge is available before querying specific resources.

    Returns:
        JSON array of resource ID strings, e.g. ["geopolitical/norway_russia", ...]
    """
    return json.dumps(list(KNOWLEDGE_REGISTRY.keys()))


@mcp.tool
def read_knowledge_base(resource_id: str) -> str:
    """Read a knowledge bank resource by its ID.

    Use list_knowledge_base() first to discover available resource IDs.

    Args:
        resource_id: The resource identifier, e.g. "geopolitical/norway_russia",
                     "sectors/energy", or "threat_actors/russian_state".

    Returns:
        The full markdown content of the requested resource.

    Raises:
        ValueError: If resource_id is not in the registry or file not found.
    """
    if resource_id not in KNOWLEDGE_REGISTRY:
        available = list(KNOWLEDGE_REGISTRY.keys())
        raise ValueError(
            f"Unknown resource_id: '{resource_id}'. Available: {available}"
        )

    path = RESOURCES_DIR / f"{resource_id}.md"
    if not path.exists():
        raise ValueError(f"Resource file not found: {resource_id}")

    return path.read_text(encoding="utf-8")


# ── OSINT Tools (Collection phase) ───────────────────────────────────────────
# TODO: Implement query_otx, search_misp, search_local_data


# ── Processing Tools ─────────────────────────────────────────────────────────
# TODO: Implement normalize_data, enrich_ioc, map_to_mitre


# ── Health check ─────────────────────────────────────────────────────────────

@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    print("Health check — server is running.", file=stderr, flush=True)
    return JSONResponse({"status": "ok"})


# ── Test tool ────────────────────────────────────────────────────────────────

@mcp.tool
def greet() -> str:
    """Test tool to verify the server is running."""
    print("MCP greet() called — server is running.", file=stderr, flush=True)
    return "MCP Threat Intelligence Server is running."


if __name__ == "__main__":
    import os

    port = int(os.getenv("MCP_SERVER_PORT", "8001"))
    mcp.run(transport="sse", host="127.0.0.1", port=port, show_banner=False, log_level="INFO")
