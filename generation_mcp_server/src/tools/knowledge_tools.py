"""Knowledge Bank MCP resources and tools.

Reads from knowledge.db when available, falls back to file-based .md resources.
"""

import json
import logging

from fastmcp import Context
from resources import KNOWLEDGE_REGISTRY, RESOURCES_DIR
from tools.local_search import _get_tlp_level, _RESTRICTED_TLP, _USE_LOCAL, _maybe_elicit_provider_switch

logger = logging.getLogger("mcp_server")


def _db_list_ids() -> list[str] | None:
    """Return all resource IDs from knowledge.db, or None if unavailable."""
    try:
        from db import get_knowledge_connection
        conn = get_knowledge_connection()
        rows = conn.execute("SELECT id FROM knowledge_resources ORDER BY id").fetchall()
        conn.close()
        return [r["id"] for r in rows]
    except Exception:
        return None


def _db_read(resource_id: str) -> str | None:
    """Read markdown content from knowledge.db, or None if unavailable."""
    try:
        from db import get_knowledge_connection
        conn = get_knowledge_connection()
        row = conn.execute(
            "SELECT markdown_content FROM knowledge_resources WHERE id = ?",
            (resource_id,),
        ).fetchone()
        conn.close()
        if row:
            return row["markdown_content"]
    except Exception:
        pass
    return None


def _db_index() -> list[dict] | None:
    """Return the full knowledge index from DB, or None if unavailable."""
    try:
        from db import get_knowledge_connection
        conn = get_knowledge_connection()
        rows = conn.execute(
            "SELECT id, keywords, priority, citation FROM knowledge_resources ORDER BY id"
        ).fetchall()
        conn.close()
        return [
            {
                "uri": f"knowledge://{r['id']}",
                "id": r["id"],
                "keywords": json.loads(r["keywords"]) if r["keywords"] else [],
                "priority": r["priority"],
                "citation": json.loads(r["citation"]) if r["citation"] else None,
            }
            for r in rows
        ]
    except Exception:
        return None


def list_knowledge_base() -> str:
    """List all available knowledge bank resource IDs."""
    db_ids = _db_list_ids()
    if db_ids is not None:
        return json.dumps(db_ids)
    # Fallback
    return json.dumps(list(KNOWLEDGE_REGISTRY.keys()))


async def read_knowledge_base(ctx: Context, resource_id: str, session_id: str) -> str:
    """Read a knowledge bank resource by its ID.

    session_id is required so classified content (TLP:RED/AMBER) can trigger
    a one-time provider-switch elicitation for the correct session.
    If the content carries a restricted TLP level and the session has not yet
    been warned, fires the elicitation before returning the content.
    """
    db_content = _db_read(resource_id)
    if db_content is not None:
        content = db_content
    else:
        if resource_id not in KNOWLEDGE_REGISTRY:
            available = list(KNOWLEDGE_REGISTRY.keys())
            raise ValueError(
                f"Unknown resource_id: '{resource_id}'. Available: {available}"
            )
        path = RESOURCES_DIR / f"{resource_id}.md"
        if not path.exists():
            raise ValueError(f"Resource file not found: {resource_id}")
        content = path.read_text(encoding="utf-8")

    tlp_level = _get_tlp_level(content[:300])
    if tlp_level in _RESTRICTED_TLP:
        choice = await _maybe_elicit_provider_switch(ctx, session_id, tlp_level)
        if choice == _USE_LOCAL:
            return f"Innhold ikke returnert — bruker valgte lokal LLM for {tlp_level}-ressurs."

    return content


def register_knowledge_tools(mcp) -> None:
    mcp.tool(list_knowledge_base)
    mcp.tool(read_knowledge_base)


def register_knowledge_resources(mcp) -> None:
    @mcp.resource("knowledge://index", mime_type="application/json")
    def knowledge_index() -> str:
        """Index of all knowledge bank resources with their keywords and URIs."""
        db_index = _db_index()
        if db_index is not None:
            return json.dumps(db_index)

        # Fallback
        return json.dumps(
            [
                {
                    "uri": f"knowledge://{resource_id}",
                    "id": resource_id,
                    "keywords": entry["keywords"],
                    "priority": entry["priority"],
                    "citation": entry.get("citation"),
                }
                for resource_id, entry in KNOWLEDGE_REGISTRY.items()
            ]
        )

    @mcp.resource("knowledge://{category}/{name}", mime_type="text/markdown")
    def knowledge_resource(category: str, name: str) -> str:
        """Read a specific knowledge bank resource by category and name."""
        resource_id = f"{category}/{name}"

        # Try DB first
        db_content = _db_read(resource_id)
        if db_content is not None:
            return db_content

        # Fallback to file
        if resource_id not in KNOWLEDGE_REGISTRY:
            available = list(KNOWLEDGE_REGISTRY.keys())
            raise ValueError(f"Unknown resource: '{resource_id}'. Available: {available}")

        path = RESOURCES_DIR / f"{resource_id}.md"
        if not path.exists():
            raise ValueError(f"Resource file not found: {resource_id}")

        return path.read_text(encoding="utf-8")
