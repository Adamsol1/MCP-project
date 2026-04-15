"""Council MCP HTTP Server — exposes the deliberate tool via HTTP/SSE.

This server runs on port 8003 and is the entry point for backend integration.
The backend connects via MCPClient → call_tool("deliberate", {...}).

The stdio server (server.py) remains unchanged for Claude Desktop integration.

Architecture:
  server.py      — stdio transport (Claude Desktop)
  server_http.py — HTTP/SSE transport, port 8003 (backend MCPClient)
"""
import logging
import os
import sys
from pathlib import Path

from fastmcp import FastMCP
from starlette.responses import JSONResponse

# Ensure council_mcp package is importable
PROJECT_DIR = Path(__file__).parent.absolute()
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from adapters import create_adapter  # noqa: E402
from deliberation.engine import DeliberationEngine  # noqa: E402
from deliberation.transcript import TranscriptManager  # noqa: E402
from models.config import AdapterConfig, CLIToolConfig, load_config  # noqa: E402
from models.schema import DeliberateRequest, Participant  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(PROJECT_DIR / "mcp_server_http.log"),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Initialise config, adapters, engine  (same pattern as server.py)
# ---------------------------------------------------------------------------

config_path = PROJECT_DIR / "config.yaml"
logger.info(f"Loading config from: {config_path}")
config = load_config(str(config_path))

adapters: dict = {}
adapter_sources: list[tuple[str, dict]] = []

if hasattr(config, "adapters") and config.adapters:
    adapter_sources.append(("adapters", config.adapters))
if hasattr(config, "cli_tools") and config.cli_tools:
    adapter_sources.append(("cli_tools", config.cli_tools))

for source_name, adapter_configs in adapter_sources:
    for cli_name, cli_config in adapter_configs.items():
        if cli_name in adapters:
            continue
        try:
            adapters[cli_name] = create_adapter(cli_name, cli_config)
            logger.info(f"Initialized adapter: {cli_name} (from {source_name})")
        except Exception as e:
            logger.error(f"Failed to create adapter {cli_name}: {e}")

engine = DeliberationEngine(
    adapters=adapters,
    config=config,
    server_dir=PROJECT_DIR,
)
# Council debates work from a prepared dossier — disable file-system tools
# to avoid prompt contamination from unrelated files in the working directory.
engine.tool_executor = None
engine.tool_execution_history = []

logger.info("DeliberationEngine ready")

# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="ai-counsel",
    instructions=(
        "Council deliberation server. "
        "Use the deliberate tool to run a multi-perspective AI deliberation."
    ),
)


@mcp.tool()
async def deliberate(
    question: str,
    participants: list[dict],
    rounds: int = 2,
    mode: str = "quick",
    context: str | None = None,
    working_directory: str | None = None,
) -> dict:
    """Run a multi-round deliberation between AI participants.

    Args:
        question:          The analytical question or debate point.
        participants:      List of participant dicts with keys: cli, model,
                           display_name (optional), persona_prompt (optional).
        rounds:            Number of debate rounds (1-5, default 2).
        mode:              "quick" or "conference".
        context:           Shared background text injected into round 1.
        working_directory: Working directory for the deliberation engine.
                           Defaults to the server's project directory.

    Returns:
        DeliberationResult as a JSON-serialisable dict.
    """
    if working_directory is None:
        working_directory = str(PROJECT_DIR)

    logger.info(f"deliberate called: {question[:60]}...")

    request = DeliberateRequest(
        question=question,
        participants=[Participant(**p) for p in participants],
        rounds=rounds,
        mode=mode,
        context=context,
        working_directory=working_directory,
    )

    result = await engine.execute(request)
    logger.info(
        f"Deliberation complete: {result.rounds_completed} rounds, status: {result.status}"
    )
    return result.model_dump()


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return JSONResponse({"status": "ok", "server": "council"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("COUNCIL_MCP_PORT", "8003"))
    logger.info(f"Starting Council MCP HTTP server on port {port}...")
    mcp.run(transport="sse", host="127.0.0.1", port=port)
