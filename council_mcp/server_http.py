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
import sqlite3
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
from deliberation.summarizer import DeliberationSummarizer  # noqa: E402
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


def _configure_local_openai_adapter() -> None:
    provider = os.getenv("LLM_PROVIDER", "local").strip().lower()
    if provider in {"gemini", "gemini-api", "gemini_api", "google"}:
        return
    adapter_config = getattr(config, "adapters", {}).get("openai")
    if adapter_config is None:
        return
    adapter_config.base_url = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8000/v1")
    adapter_config.api_key = os.getenv("LLM_API_KEY", "my-secret-key")
    timeout = os.getenv("LLM_TIMEOUT_SECONDS") or os.getenv("VLLM_TIMEOUT_SECONDS")
    if timeout:
        try:
            adapter_config.timeout = int(timeout)
        except ValueError:
            logger.warning("Ignoring invalid LLM_TIMEOUT_SECONDS=%s", timeout)


_configure_local_openai_adapter()

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
# Knowledge DB access
# ---------------------------------------------------------------------------

_DB_PATH = PROJECT_DIR.parent / "backend" / "data" / "knowledge.db"


def _read_persona(perspective: str) -> str:
    """Read persona markdown from knowledge.db for a given perspective."""
    if not _DB_PATH.exists():
        raise RuntimeError(f"knowledge.db not found at {_DB_PATH}")
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT markdown_content FROM knowledge_resources WHERE id = ?",
            (f"personas/{perspective.lower()}",),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise ValueError(f"No persona found for perspective: '{perspective}'")
    return row["markdown_content"]


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


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@mcp.resource("knowledge://personas/{perspective}", mime_type="text/markdown")
def persona_resource(perspective: str) -> str:
    """Analytical persona for a council participant.

    Fetched by the backend for each selected perspective before building
    the participants list for a deliberation.

    Args:
        perspective: One of: us, norway, china, eu, russia, neutral.
    """
    return _read_persona(perspective)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

@mcp.prompt()
def council_behavior() -> str:
    """Debate behavior instructions shared by all council participants.

    Injected into each participant's persona_prompt alongside the
    perspective-specific persona from knowledge://personas/{perspective}.
    """
    return (
        "You are participating in a structured multi-round analytical debate.\n"
        "Represent your assigned perspective authentically and consistently.\n"
        "Argue positions that align with your values and strategic priorities.\n"
        "Challenge other participants' assessments where they conflict with your perspective.\n"
        "Do not concede your position without solid evidence from the shared context.\n"
        "Be direct and concrete — avoid vague platitudes.\n"
        "Each response should advance the debate, not merely summarise what others have said."
    )


@mcp.prompt()
def council_task(analysis_draft: str, findings: str, debate_point: str) -> str:
    """Debate briefing shared with all council participants as context.

    Replaces the inline build_context() in CouncilService.
    Provides the shared evidence base and debate focus for the deliberation.

    Args:
        analysis_draft: JSON-serialised AnalysisDraft from the analysis phase.
        findings:       JSON-serialised list of ProcessingResult findings.
        debate_point:   The specific question or focus for the debate.
    """
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


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

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


@mcp.tool()
async def summarize_entries(
    entries: list[dict],
    adapter: str = "gemini",
    model: str = "gemini-2.5-flash",
) -> list[dict]:
    """Generate a one-sentence AI summary for each council transcript entry.

    Args:
        entries:  List of dicts with keys: round (int), participant (str), response (str).
        adapter:  Adapter name to use for summarization (default: gemini).
        model:    Model identifier for the chosen adapter.

    Returns:
        List of dicts with keys: round, participant, summary.
    """
    chosen_adapter = adapters.get(adapter) or (next(iter(adapters.values())) if adapters else None)
    if chosen_adapter is None:
        raise RuntimeError("No adapters available for summarization")

    # Strip VOTE blocks and truncate responses before sending to the model
    items = []
    for entry in entries:
        response_text = entry.get("response", "")
        vote_index = response_text.rfind("VOTE:")
        body = response_text[:vote_index].strip() if vote_index != -1 else response_text.strip()
        items.append({
            "round": entry.get("round"),
            "participant": entry.get("participant"),
            "body": body[:1500],
        })

    entries_text = "\n\n".join(
        f"Round {item['round']} — {item['participant']}:\n{item['body']}"
        for item in items
    )

    prompt = (
        "For each analyst response below, write a single sentence (max 180 characters) "
        "capturing the analyst's core strategic position and key finding. "
        "Be specific — name the key claim, not just the topic.\n\n"
        "Return ONLY a JSON array. Each element must have exactly these keys: "
        "round (integer), participant (string), summary (string). "
        "Preserve the exact round number and participant name from the input.\n\n"
        f"{entries_text}"
    )

    try:
        raw_text = await chosen_adapter.invoke(prompt=prompt, model=model, context=None)
        # Strip markdown fences if present
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()
        # Extract JSON array
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            text = text[start : end + 1]
        import json
        result = json.loads(text)
        return [
            {"round": int(r["round"]), "participant": str(r["participant"]), "summary": str(r["summary"])}
            for r in result
            if "round" in r and "participant" in r and "summary" in r
        ]
    except Exception as exc:
        logger.warning(f"summarize_entries failed: {exc}")
        return []


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
