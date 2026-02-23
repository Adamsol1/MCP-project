import json
import logging
from pathlib import Path

logger = logging.getLogger("app")


class ResearchLogger:
    def __init__(self, log_path=None, session_id=None):
        # Use given log_path
        if log_path:
            self.log_path = Path(log_path)
        # Use default logpath
        else:
            self.log_path = Path(
                f"data/outputs/research_log_{session_id}.jsonl"
            )

        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def create_log(self, log_entry):
        # Convert Pydantic model to dict, then to json
        if hasattr(log_entry, "model_dump"):
            log_entry = log_entry.model_dump(mode="json")
        converted_log = json.dumps(log_entry)

        try:
            with open(self.log_path, "a") as f:
                f.write(converted_log + "\n")
        except OSError as e:
            logger.error(f"[ResearchLogger] Failed to write log entry: {e}")

    def write_reasoning_log(self, reasoning_log: "ReasoningLog") -> None:
        log_path = Path(f"data/outputs/reasoning_log_{reasoning_log.session_id}.json")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(log_path, "w") as f:
                f.write(reasoning_log.model_dump_json(indent=2))
        except OSError as e:
            logger.error(f"[ResearchLogger] Failed to write reasoning log: {e}")
