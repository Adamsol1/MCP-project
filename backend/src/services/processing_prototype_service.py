"""Service for loading processing results — session data first, demo fallback."""

import json
import logging
import re
from pathlib import Path

from pydantic import ValidationError

from src.models.analysis import ProcessingResult

logger = logging.getLogger(__name__)

_SESSIONS_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "sessions"
_DEMO_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "outputs" / "demo_processing_result.json"
)


def _try_parse_processing_result(raw: str) -> ProcessingResult | None:
    """Attempt to extract a ProcessingResult from raw LLM output.

    Handles both plain JSON and JSON wrapped in markdown code fences.
    """
    # Try to extract JSON from markdown code blocks first
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    candidate = match.group(1) if match else raw.strip()

    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict) or "findings" not in payload:
        return None

    try:
        return ProcessingResult.model_validate(payload)
    except ValidationError:
        return None


class ProcessingPrototypeService:
    """Loads a processing result from session data, falling back to demo."""

    def __init__(self, prototype_path: str | Path | None = None):
        if prototype_path is None:
            prototype_path = _DEMO_PATH
        self.prototype_path = Path(prototype_path)

    def get_processing_result(
        self, session_id: str
    ) -> tuple[ProcessingResult, str]:
        """Load a processing result for the given session.

        Returns a tuple of (ProcessingResult, data_source) where data_source
        is "session" or "demo".

        Priority:
        1. Session processed.json (last attempt, parsed as ProcessingResult)
        2. Demo/prototype fallback from self.prototype_path
        """
        session_result = self._try_load_session(session_id)
        if session_result is not None:
            logger.info(
                "Loaded processing result from session %s processed.json", session_id
            )
            return session_result, "session"

        logger.info(
            "No session data for %s, falling back to demo at %s",
            session_id,
            self.prototype_path,
        )
        return self._load_demo(), "demo"

    def _try_load_session(self, session_id: str) -> ProcessingResult | None:
        """Try to load a ProcessingResult from the session's processed.json."""
        processed_path = _SESSIONS_DATA_DIR / session_id / "processed.json"
        if not processed_path.exists():
            return None

        try:
            data = json.loads(processed_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Failed to read/parse %s", processed_path)
            return None

        attempts = data.get("attempts", [])
        if not attempts:
            return None

        # Try the last attempt first (most recent), then earlier ones
        for attempt in reversed(attempts):
            if not isinstance(attempt, str):
                continue
            result = _try_parse_processing_result(attempt)
            if result is not None:
                return result

        logger.info("No valid ProcessingResult found in %s attempts", len(attempts))
        return None

    def _load_demo(self) -> ProcessingResult:
        """Load and validate the demo/prototype processing result."""
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
