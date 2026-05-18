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
    """Return True if an HTTP GET on /health responds with 2xx.

    Used by the preflight check at startup to detect that the Review MCP is
    already running on the target port. A short timeout keeps boot fast when
    no server is present.
    """
    try:
        with urlopen(f"http://127.0.0.1:{port}/health", timeout=0.3) as response:
            return 200 <= response.status < 300
    except (OSError, URLError):
        return False


def _port_in_use(port: int) -> bool:
    """Return True if the port is bound by some process, ours or not.

    Distinguishes "already running and healthy" from "port taken by something
    else" so the caller can choose between a clean exit and a hard error.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


# Defaults to 8002 unless REVIEW_MCP_PORT overrides it. The generation MCP
# claims 8001, so the review server intentionally takes the next port up.
BOOT_PORT = int(os.getenv("REVIEW_MCP_PORT", "8002"))
BOOT_URL = f"http://127.0.0.1:{BOOT_PORT}/sse"

# ── Preflight ─────────────────────────────────────────────────────────────────
# Runs before importing heavy dependencies so a duplicate launch exits quickly
# without paying the cost of loading FastMCP and Starlette.
if __name__ == "__main__":
    if _health_ok(BOOT_PORT):
        print(f"Review MCP already running on {BOOT_URL}", flush=True)
        raise SystemExit(0)
    if _port_in_use(BOOT_PORT):
        # Port is taken but /health did not answer, so something else owns it.
        # Surface a concrete next step rather than letting FastMCP fail later.
        print(
            f"Review MCP port {BOOT_PORT} is already in use. Stop the other process or set REVIEW_MCP_PORT.",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)

# ── Dependencies ──────────────────────────────────────────────────────────────
# Guarded so a missing dependency produces one readable error pointing the
# operator at the right project to `poetry install` in, instead of a raw
# traceback that buries the actual cause.
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

# Loads .env from the current working directory if present. Used to pick up
# REVIEW_MCP_PORT and any future configuration without baking values into code.
load_dotenv()

# ── MCP server setup ──────────────────────────────────────────────────────────
# The `instructions` string is surfaced to clients during MCP discovery, so it
# doubles as inline documentation for anyone inspecting the server.
mcp = FastMCP(
    name="ReviewServer",
    instructions=(
        "MCP server providing review prompt templates for AI #2. "
        "Each prompt instructs the reviewer how to evaluate output from a specific "
        "intelligence phase (Direction, Collection, Processing)."
    ),
)

# All phase prompts live in the prompts subpackage. Registration happens here
# (rather than inside FastMCP) to keep the server file focused on transport.
register_prompts(mcp)


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    """Liveness probe consumed by the preflight check and any external monitor."""
    return JSONResponse({"status": "ok", "server": "review"})


# ── Entrypoint ────────────────────────────────────────────────────────────────
# Banner is suppressed and log level raised to WARNING so the Review MCP stays
# quiet when launched as a child process of the backend; the parent's logs
# remain the canonical source of operator output.
if __name__ == "__main__":
    print(f"Starting Review MCP on {BOOT_URL}", flush=True)
    mcp.run(
        transport="sse",
        host="127.0.0.1",
        port=BOOT_PORT,
        show_banner=False,
        log_level="WARNING",
    )
