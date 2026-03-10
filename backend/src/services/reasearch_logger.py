import json
import logging
from pathlib import Path

from src.models.reasoning import ReasoningLog

logger = logging.getLogger("app")


class ResearchLogger:
    """
    Writes session logs to disk in JSON format

    Uses two different log types:
    - research_log_{session_id}.jsonl .Append one entry per line (user actions + AI attempts)
    - reasoning_log_{session_id}.json  .Single file written on PIR approval (full reasoning trace)

    """

    def __init__(self, log_path=None, session_id=None):
        # Use given log_path
        if log_path:
            self.log_path = Path(log_path)
        # Use default logpath
        else:
            self.log_path = Path(__file__).resolve().parents[2] / "data" / "outputs" / f"research_log_{session_id}.jsonl"

        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def create_log(self, log_entry):
        "Append single log entry to sessions JSON log"
        # Convert Pydantic model to dict, then to json
        if hasattr(log_entry, "model_dump"):
            log_entry = log_entry.model_dump(mode="json")
        converted_log = json.dumps(log_entry)
        # Attempt to write to disk
        try:
            with open(self.log_path, "a") as f:
                f.write(converted_log + "\n")
        # Cast error if unsuccesfull.
        except OSError as e:
            logger.error(f"[ResearchLogger] Failed to write log entry: {e}")

    def write_reasoning_log(self, reasoning_log: "ReasoningLog") -> None:
        """
        Writes fulll reasoning log to JSON file.
        """
        log_path = Path(__file__).resolve().parents[2] / "data" / "outputs" / f"reasoning_log_{reasoning_log.session_id}.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(log_path, "w") as f:
                f.write(reasoning_log.model_dump_json(indent=2))
        except OSError as e:
            logger.error(f"[ResearchLogger] Failed to write reasoning log: {e}")
