"""Prototype service for loading processing results from a placeholder JSON file."""

import json
from pathlib import Path

from pydantic import ValidationError

from src.models.analysis import ProcessingResult


class ProcessingPrototypeService:
    """Loads a prototype processing result from disk."""

    def __init__(self, prototype_path: str | Path | None = None):
        if prototype_path is None:
            prototype_path = (
                Path(__file__).resolve().parents[2]
                / "data"
                / "outputs"
                / "demo_processing_result.json"
            )
        self.prototype_path = Path(prototype_path)

    def get_processing_result(self, session_id: str) -> ProcessingResult:
        """Load and validate the prototype processing result.

        The session_id parameter is currently unused, but retained so the
        interface remains compatible with a future session-backed implementation.
        """
        del session_id

        try:
            raw_payload = self.prototype_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(
                f"Failed to load processing result from {self.prototype_path}"
            ) from exc

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Failed to parse processing result JSON from {self.prototype_path}"
            ) from exc

        try:
            return ProcessingResult.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(
                f"Failed to validate processing result from {self.prototype_path}"
            ) from exc
