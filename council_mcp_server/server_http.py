"""Council MCP HTTP Server - exposes the deliberate tool via HTTP/SSE.

This server runs on port 8003 and is the entry point for backend integration.
The backend connects via MCPClient -> call_tool("deliberate", {...}).

The stdio server (server.py) remains unchanged for Claude Desktop integration.

Architecture:
  server.py      - stdio transport (Claude Desktop)
  server_http.py - HTTP/SSE transport, port 8003 (backend MCPClient)
"""

import logging
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


PROJECT_DIR = Path(__file__).parent.absolute()
BOOT_PORT = int(os.getenv("COUNCIL_MCP_PORT", "8003"))
BOOT_URL = f"http://127.0.0.1:{BOOT_PORT}/sse"

if __name__ == "__main__":
    if _health_ok(BOOT_PORT):
        print(f"Council MCP already running on {BOOT_URL}", flush=True)
        raise SystemExit(0)
    if _port_in_use(BOOT_PORT):
        print(
            f"Council MCP port {BOOT_PORT} is already in use. Stop the other process or set COUNCIL_MCP_PORT.",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)

try:
    from fastmcp import FastMCP
    from starlette.responses import JSONResponse
except ModuleNotFoundError as exc:
    print(
        f"Missing Python dependency '{exc.name}' in council_mcp_server. Run `poetry install` in council_mcp_server.",
        file=sys.stderr,
        flush=True,
    )
    raise SystemExit(1)

# Ensure council_mcp package is importable
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
file_handler = logging.FileHandler(PROJECT_DIR / "mcp_server_http.log")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
stream_handler = logging.StreamHandler(sys.stderr)
stream_handler.setLevel(logging.WARNING)
stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))

from adapters import create_adapter  # noqa: E402
from deliberation.engine import DeliberationEngine  # noqa: E402
from deliberation.summarizer import DeliberationSummarizer  # noqa: E402
from deliberation.transcript import TranscriptManager  # noqa: E402
from models.config import AdapterConfig, CLIToolConfig, load_config  # noqa: E402
from models.schema import DeliberateRequest, Participant  # noqa: E402
from personas import get_persona  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, stream_handler],
    force=True,
)
logger = logging.getLogger(__name__)

config_path = PROJECT_DIR / "config.yaml"
logger.info("Loading config from: %s", config_path)
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
            logger.info("Initialized adapter: %s (from %s)", cli_name, source_name)
        except Exception as exc:
            logger.error("Failed to create adapter %s: %s", cli_name, exc)

engine = DeliberationEngine(
    adapters=adapters,
    config=config,
    server_dir=PROJECT_DIR,
)
engine.tool_executor = None
engine.tool_execution_history = []

logger.info("DeliberationEngine ready")

mcp = FastMCP(
    name="ai-counsel",
    instructions=(
        "Council deliberation server. "
        "Use the deliberate tool to run a multi-perspective AI deliberation."
    ),
)


@mcp.prompt()
def persona(perspective: str) -> str:
    """Analytical persona for a council participant."""
    return get_persona(perspective)


@mcp.prompt()
def council_behavior() -> str:
    """Debate behavior instructions shared by all council participants."""
    return (
        "You are participating in a structured multi-round analytical debate.\n"
        "Represent your assigned perspective authentically and consistently.\n"
        "Argue positions that align with your values and strategic priorities.\n"
        "Challenge other participants' assessments where they conflict with your perspective.\n"
        "Do not concede your position without solid evidence from the shared context.\n"
        "Be direct and concrete - avoid vague platitudes.\n"
        "Each response should advance the debate, not merely summarise what others have said."
    )


@mcp.prompt()
def council_task(analysis_draft: str, findings: str, debate_point: str) -> str:
    """Debate briefing shared with all council participants as context."""
    focus = debate_point.strip() or (
        "Assess the strongest interpretation and strategic implications of the findings above."
    )
    return (
        "## Intelligence Analysis Draft\n"
        f"{analysis_draft}\n\n"
        "## Key Findings\n"
        f"{findings}\n\n"
        "## Debate Focus\n"
        f"{focus}\n\n"
        "Use the analysis and findings above as your primary evidence base.\n"
        "Do not introduce information not present in the provided material."
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
    """Run a multi-round deliberation between AI participants."""
    if working_directory is None:
        working_directory = str(PROJECT_DIR)

    logger.info("deliberate called: %s...", question[:60])

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
        "Deliberation complete: %s rounds, status: %s",
        result.rounds_completed,
        result.status,
    )
    return result.model_dump()


@mcp.tool()
async def summarize_entries(
    entries: list[dict],
    adapter: str = "gemini",
    model: str = "gemini-2.5-flash",
) -> list[dict]:
    """Generate a one-sentence AI summary for each council transcript entry."""
    chosen_adapter = adapters.get(adapter) or (next(iter(adapters.values())) if adapters else None)
    if chosen_adapter is None:
        raise RuntimeError("No adapters available for summarization")

    items = []
    for entry in entries:
        response_text = entry.get("response", "")
        vote_index = response_text.rfind("VOTE:")
        body = response_text[:vote_index].strip() if vote_index != -1 else response_text.strip()
        items.append(
            {
                "round": entry.get("round"),
                "participant": entry.get("participant"),
                "body": body[:1500],
            }
        )

    entries_text = "\n\n".join(
        f"Round {item['round']} - {item['participant']}:\n{item['body']}"
        for item in items
    )

    prompt = (
        "For each analyst response below, write a single sentence (max 180 characters) "
        "capturing the analyst's core strategic position and key finding. "
        "Be specific - name the key claim, not just the topic.\n\n"
        "Return ONLY a JSON array. Each element must have exactly these keys: "
        "round (integer), participant (string), summary (string). "
        "Preserve the exact round number and participant name from the input.\n\n"
        f"{entries_text}"
    )

    try:
        raw_text = await chosen_adapter.invoke(prompt=prompt, model=model, context=None)
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            text = text[start : end + 1]
        import json

        result = json.loads(text)
        return [
            {
                "round": int(row["round"]),
                "participant": str(row["participant"]),
                "summary": str(row["summary"]),
            }
            for row in result
            if "round" in row and "participant" in row and "summary" in row
        ]
    except Exception as exc:
        logger.warning("summarize_entries failed: %s", exc)
        return []


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return JSONResponse({"status": "ok", "server": "council"})


if __name__ == "__main__":
    print(f"Starting Council MCP on {BOOT_URL}", flush=True)
    mcp.run(
        transport="sse",
        host="127.0.0.1",
        port=BOOT_PORT,
        show_banner=False,
        log_level="WARNING",
    )
