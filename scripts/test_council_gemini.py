"""Run a minimal Gemini-backed council_mcp deliberation from the terminal.

Usage:
    python scripts/test_council_gemini.py "Should we keep using this council MCP?"
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
COUNCIL_DIR = ROOT / "council_mcp"


def load_repo_env() -> None:
    """Load simple KEY=VALUE pairs from the repo .env into this process."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def configure_logging_for_terminal() -> None:
    """Hide noisy server logs and keep terminal output focused."""
    logging.disable(logging.CRITICAL)


async def run(question: str) -> int:
    """Execute a minimal quick-mode Gemini deliberation."""
    sys.path.insert(0, str(COUNCIL_DIR))

    import server  # noqa: PLC0415

    # Keep terminal testing fast and Gemini-only.
    server.config.deliberation.file_tree.enabled = False
    server.engine.config.deliberation.file_tree.enabled = False

    if getattr(server.config, "decision_graph", None):
        server.config.decision_graph.enabled = False
        server.engine.config.decision_graph.enabled = False
    server.engine.graph_integration = None

    server.engine.summarizer_chain = [
        item for item in server.engine.summarizer_chain if item[0] is server.adapters["gemini"]
    ]

    args = {
        "question": question,
        "participants": [
            {"cli": "gemini", "model": "gemini-2.5-pro"},
            {"cli": "gemini", "model": "gemini-2.5-pro"},
        ],
        "mode": "quick",
        "rounds": 1,
        "working_directory": str(ROOT),
    }

    result = await server.call_tool("deliberate", args)
    data = json.loads(result[0].text)

    issues = data.get("issues") or []
    summary = data.get("summary") or {}

    print(f"status: {data.get('status')}")
    print(f"rounds: {data.get('rounds_completed')}")
    print(f"transcript: {data.get('transcript_path')}")
    print()

    if isinstance(summary, dict):
        print("consensus:")
        print(summary.get("consensus", "(none)"))
        print()
        print("recommendation:")
        print(summary.get("final_recommendation", "(none)"))

    if issues:
        print()
        print("issues:")
        for issue in issues:
            print(f"- {issue}")

    return 0 if data.get("status") == "complete" and not issues else 1


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python scripts/test_council_gemini.py "Your question here"')
        return 2

    if not (ROOT / ".env").exists():
        print("Missing .env in repo root.")
        return 2

    load_repo_env()

    if not os.getenv("GEMINI_API_KEY"):
        print("GEMINI_API_KEY is not set in .env.")
        return 2

    question = " ".join(sys.argv[1:]).strip()
    if len(question) < 10:
        print("Question must be at least 10 characters.")
        return 2

    configure_logging_for_terminal()
    return asyncio.run(run(question))


if __name__ == "__main__":
    raise SystemExit(main())
