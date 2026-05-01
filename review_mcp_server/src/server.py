"""Review MCP Server - AI #2 review prompts for all intelligence phases.

This server is exclusively for the review agent (AI #2). It exposes review
prompt templates via the MCP Prompts primitive. ReviewService connects here
to fetch the appropriate review prompt for each phase, then calls LLMService
(Gemini) with that prompt.

Architecture:
  Port 8001 - Generation server (mcp_server/) - Agent #1 connects here
  Port 8002 - Review server (this file)        - Agent #2 connects here

This separation ensures Agent #1 cannot use review prompts and Agent #2
cannot accidentally call OSINT tools.
"""

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


BOOT_PORT = int(os.getenv("REVIEW_MCP_PORT", "8002"))
BOOT_HOST = os.getenv("REVIEW_MCP_HOST", "127.0.0.1")
BOOT_URL = f"http://127.0.0.1:{BOOT_PORT}/sse"

if __name__ == "__main__":
    if _health_ok(BOOT_PORT):
        print(f"Review MCP already running on {BOOT_URL}", flush=True)
        raise SystemExit(0)
    if _port_in_use(BOOT_PORT):
        print(
            f"Review MCP port {BOOT_PORT} is already in use. Stop the other process or set REVIEW_MCP_PORT.",
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

from prompts import register_prompts

load_dotenv()

mcp = FastMCP(
    name="ReviewServer",
    instructions=(
        "MCP server providing review prompt templates for AI #2. "
        "Each prompt instructs the reviewer how to evaluate output from a specific "
        "intelligence phase (Direction, Collection, Processing)."
    ),
)

register_prompts(mcp)


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return JSONResponse({"status": "ok", "server": "review"})


if __name__ == "__main__":
    print(f"Starting Review MCP on {BOOT_URL}", flush=True)
    mcp.run(
        transport="sse",
        host=BOOT_HOST,
        port=BOOT_PORT,
        show_banner=False,
        log_level="WARNING",
    )
