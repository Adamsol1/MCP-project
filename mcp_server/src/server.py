"""MCP Threat Intelligence Server — Generation Server (port 8001).

This server is for Agent #1 (GeminiAgent). It provides:
  - Tools: OSINT sources, knowledge bank access, data processing
  - Prompts: System prompt templates for Direction and Collection phases

The review server (port 8002) is a separate process for Agent #2.
"""

import json
import os
from pathlib import Path
from sys import stderr

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.responses import JSONResponse

from prompts import (
    build_direction_dialogue_prompt,
    build_pir_generation_prompt,
    build_summary_prompt,
)
from resources import KNOWLEDGE_REGISTRY, RESOURCES_DIR

load_dotenv()

print("Starting MCP Threat Intelligence Server...", file=stderr, flush=True)

mcp = FastMCP(
    name="ThreatIntelligence",
    instructions="MCP server providing OSINT tools and knowledge bank resources for the Collection and Processing phases of the Threat Intelligence cycle.",
)


# ── Knowledge Bank Resources ──────────────────────────────────────────────────

@mcp.resource("knowledge://index", mime_type="application/json")
def knowledge_index() -> str:
    """Index of all knowledge bank resources with their keywords and URIs.

    Read this to discover what knowledge is available and which resources
    are relevant to an investigation. Use the keywords to match against
    context fields (scope, target_entities, threat_actors).

    Returns:
        JSON array of resource descriptors with uri, id, keywords, priority fields.
    """
    return json.dumps([
        {
            "uri": f"knowledge://{resource_id}",
            "id": resource_id,
            "keywords": entry["keywords"],
            "priority": entry["priority"],
        }
        for resource_id, entry in KNOWLEDGE_REGISTRY.items()
    ])


@mcp.resource("knowledge://{category}/{name}", mime_type="text/markdown")
def knowledge_resource(category: str, name: str) -> str:
    """Read a specific knowledge bank resource by category and name.

    Args:
        category: Resource category — geopolitical, sectors, or threat_actors.
        name: Resource name within its category, e.g. norway_russia, energy.

    Returns:
        Full markdown content of the knowledge resource.

    Raises:
        ValueError: If the resource does not exist.
    """
    resource_id = f"{category}/{name}"
    if resource_id not in KNOWLEDGE_REGISTRY:
        available = list(KNOWLEDGE_REGISTRY.keys())
        raise ValueError(f"Unknown resource: '{resource_id}'. Available: {available}")

    path = RESOURCES_DIR / f"{resource_id}.md"
    if not path.exists():
        raise ValueError(f"Resource file not found: {resource_id}")

    return path.read_text(encoding="utf-8")


# ── Knowledge Bank Tools ───────────────────────────────────────────────────────

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


# ── Direction Prompts ─────────────────────────────────────────────────────────

@mcp.prompt
def direction_gathering(
    user_message: str,
    missing_fields: str,
    context: str,
    language: str = "en",
) -> str:
    """Prompt for generating a clarifying question in the Direction dialogue phase.

    Args:
        user_message: The user's latest message.
        missing_fields: JSON array of context field names still missing.
        context: JSON object of the current dialogue context.
        language: BCP-47 language code (e.g. "en", "no").
    """
    ctx = json.loads(context)
    return build_direction_dialogue_prompt(
        user_message=user_message,
        missing_fields=json.loads(missing_fields),
        perspectives=ctx.get("perspectives", []),
        context=ctx,
        language=language,
    )


@mcp.prompt
def direction_summary(
    scope: str,
    timeframe: str,
    target_entities: str,
    threat_actors: str,
    priority_focus: str,
    perspectives: str,
    modifications: str = "",
    language: str = "en",
) -> str:
    """Prompt for generating a context summary in the Direction phase.

    Args:
        scope: The focus area of the investigation.
        timeframe: The time period of the investigation.
        target_entities: JSON array of relevant entities.
        threat_actors: JSON array of threat actors.
        priority_focus: The main aspect to emphasize.
        perspectives: JSON array of selected perspectives.
        modifications: Optional user feedback to incorporate.
        language: BCP-47 language code.
    """
    return build_summary_prompt(
        scope=scope,
        timeframe=timeframe,
        target_entities=json.loads(target_entities),
        threat_actors=json.loads(threat_actors),
        priority_focus=priority_focus,
        perspectives=json.loads(perspectives),
        modifications=modifications or None,
        language=language,
    )


@mcp.prompt
def direction_pir(
    scope: str,
    timeframe: str,
    target_entities: str,
    threat_actors: str,
    priority_focus: str,
    perspectives: str,
    modifications: str = "",
    current_pir: str = "",
    language: str = "en",
    background_knowledge: str = "",
) -> str:
    """Prompt for generating PIRs from gathered dialogue context.

    Args:
        scope: The focus area of the investigation.
        timeframe: The time period the PIR covers.
        target_entities: JSON array of relevant entities.
        threat_actors: JSON array of threat actors.
        priority_focus: The main aspect to emphasize.
        perspectives: JSON array of selected analytical perspectives.
        modifications: Optional user feedback for regenerating PIRs.
        current_pir: Existing PIR JSON string for modification requests.
        language: BCP-47 language code.
        background_knowledge: Pre-fetched knowledge content from MCP Resources,
                              injected by the backend before prompt rendering.
    """
    return build_pir_generation_prompt(
        scope=scope,
        timeframe=timeframe,
        target_entities=json.loads(target_entities),
        threat_actors=json.loads(threat_actors),
        priority_focus=priority_focus,
        perspectives=json.loads(perspectives),
        modifications=modifications or None,
        current_pir=current_pir or None,
        language=language,
        background_knowledge=background_knowledge or None,
    )


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
    port = int(os.getenv("MCP_SERVER_PORT", "8001"))
    mcp.run(transport="sse", host="127.0.0.1", port=port, show_banner=False, log_level="INFO")
