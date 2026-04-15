"""Run a minimal local-vLLM-backed council_mcp deliberation from the terminal.

Usage:
    python scripts/test_council_vllm.py "Should we keep using this council MCP?"
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
    """Execute a minimal quick-mode local-model deliberation."""
    sys.path.insert(0, str(COUNCIL_DIR))

    import server  # noqa: PLC0415
    from adapters.openai import OpenAIAdapter  # noqa: PLC0415

    base_url = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8000/v1")
    api_key = os.getenv("LLM_API_KEY", "my-secret-key")
    model = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    adapter = OpenAIAdapter(
        base_url=base_url,
        api_key=api_key,
        timeout=300,
        max_retries=1,
    )
    server.adapters["openai"] = adapter
    server.engine.adapters["openai"] = adapter

    # Keep terminal testing fast and local-model-only.
    server.config.deliberation.file_tree.enabled = False
    server.engine.config.deliberation.file_tree.enabled = False

    if getattr(server.config, "decision_graph", None):
        server.config.decision_graph.enabled = False
        server.engine.config.decision_graph.enabled = False
    server.engine.graph_integration = None

    server.engine.summarizer_chain = [(adapter, model, "local vLLM")]

    args = {
        "question": question,
        "participants": [
            {"cli": "openai", "model": model},
            {"cli": "openai", "model": model},
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
        print('Usage: python scripts/test_council_vllm.py "Your question here"')
        return 2

    load_repo_env()

    question = " ".join(sys.argv[1:]).strip()
    if len(question) < 10:
        print("Question must be at least 10 characters.")
        return 2

    configure_logging_for_terminal()
    return asyncio.run(run(question))


if __name__ == "__main__":
    raise SystemExit(main())
