"""Knowledge Bank MCP resources and tools."""

import json

from resources import KNOWLEDGE_REGISTRY, RESOURCES_DIR


def list_knowledge_base() -> str:
    """List all available knowledge bank resource IDs."""
    return json.dumps(list(KNOWLEDGE_REGISTRY.keys()))


def read_knowledge_base(resource_id: str) -> str:
    """Read a knowledge bank resource by its ID."""
    if resource_id not in KNOWLEDGE_REGISTRY:
        available = list(KNOWLEDGE_REGISTRY.keys())
        raise ValueError(
            f"Unknown resource_id: '{resource_id}'. Available: {available}"
        )

    path = RESOURCES_DIR / f"{resource_id}.md"
    if not path.exists():
        raise ValueError(f"Resource file not found: {resource_id}")

    return path.read_text(encoding="utf-8")


def register_knowledge_tools(mcp) -> None:
    mcp.tool(list_knowledge_base)
    mcp.tool(read_knowledge_base)


def register_knowledge_resources(mcp) -> None:
    # Resources use parameterised URIs so they need the decorator form
    @mcp.resource("knowledge://index", mime_type="application/json")
    def knowledge_index() -> str:
        """Index of all knowledge bank resources with their keywords and URIs."""
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
        if resource_id not in KNOWLEDGE_REGISTRY:
            available = list(KNOWLEDGE_REGISTRY.keys())
            raise ValueError(f"Unknown resource: '{resource_id}'. Available: {available}")

        path = RESOURCES_DIR / f"{resource_id}.md"
        if not path.exists():
            raise ValueError(f"Resource file not found: {resource_id}")

        return path.read_text(encoding="utf-8")
