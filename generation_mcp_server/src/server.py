"""MCP Threat Intelligence Server - Generation Server (port 8001)."""

import os
import socket
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


def _health_ok(port: int) -> bool:
    try:
        with urlopen(f"http://127.0.0.1:{port}/health", timeout=0.3) as response:
            return 200 <= response.status < 300
    except (OSError, URLError):
        return False


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


BOOT_PORT = int(os.getenv("MCP_SERVER_PORT", "8001"))
BOOT_HOST = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
BOOT_URL = f"http://127.0.0.1:{BOOT_PORT}/sse"

if __name__ == "__main__":
    if _health_ok(BOOT_PORT):
        print(f"Generation MCP already running on {BOOT_URL}", flush=True)
        raise SystemExit(0)
    if _port_in_use(BOOT_PORT):
        print(
            f"Generation MCP port {BOOT_PORT} is already in use. Stop the other process or set MCP_SERVER_PORT.",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)

try:
    from dotenv import load_dotenv
    from fastmcp import FastMCP
    from starlette.responses import JSONResponse
except ModuleNotFoundError as exc:
    project = Path(__file__).resolve().parents[1].name
    print(
        f"Missing Python dependency '{exc.name}' in {project}. Run `poetry install` in {project}.",
        file=sys.stderr,
        flush=True,
    )
    raise SystemExit(1)

# from pymisp import PyMISP  # MISP not configured on external server
from prompts import register_prompts
from resources import KNOWLEDGE_REGISTRY, RESOURCES_DIR
from tools.google_search import register_google_search_tools
from tools.knowledge_tools import register_knowledge_resources, register_knowledge_tools
from tools.local_search import register_local_search_tools
from tools.pmesii_clarification import register_processing_tools
from tools.otx_tools import register_otx_tools
from tools.session_resources import register_session_resources
from tools.upload_tools import register_upload_tools

load_dotenv()

mcp = FastMCP(
    name="ThreatIntelligence",
    instructions=(
        "MCP server providing OSINT tools and knowledge bank resources for the "
        "Collection and Processing phases of the Threat Intelligence cycle."
    ),
)

# Tools and resources registration
register_knowledge_resources(mcp)
register_session_resources(mcp)
register_knowledge_tools(mcp)
register_upload_tools(mcp)
register_google_search_tools(mcp)
register_otx_tools(mcp)
register_local_search_tools(mcp)
register_processing_tools(mcp)
register_prompts(mcp)


# Health check
@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return JSONResponse({"status": "ok"})


# Test tool

@mcp.tool
def greet() -> str:
    """Test tool to verify the server is running."""
    return "MCP Threat Intelligence Server is running."


if __name__ == "__main__":
    print(f"Starting Generation MCP on {BOOT_URL}", flush=True)
    mcp.run(
        transport="sse",
        host=BOOT_HOST,
        port=BOOT_PORT,
        show_banner=False,
        log_level="WARNING",
    )
