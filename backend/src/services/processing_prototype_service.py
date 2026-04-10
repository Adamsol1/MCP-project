"""Service for loading processing results from session artifacts only."""

import json
import logging
import re
from pathlib import Path

from pydantic import ValidationError

from src.models.analysis import ProcessingResult
from src.models.processing import ProcessingResult as LegacyProcessingResult

logger = logging.getLogger(__name__)

_SESSIONS_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "sessions"
PROCESSING_RESULT_UNAVAILABLE_MESSAGE = (
    "No processed result available for this session. Complete processing first."
)


def _try_parse_processing_result(raw: str) -> ProcessingResult | None:
    """Attempt to extract a ProcessingResult from raw LLM output."""
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    candidate = match.group(1) if match else raw.strip()

    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    if "findings" in payload:
        try:
            return ProcessingResult.model_validate(payload)
        except ValidationError:
            return None

    if "entities" in payload:
        try:
            legacy_result = LegacyProcessingResult.model_validate(payload)
        except ValidationError:
            return None
        return _convert_legacy_processing_result(legacy_result)

    return None


def _convert_legacy_processing_result(
    legacy_result: LegacyProcessingResult,
) -> ProcessingResult:
    """Convert the older PMESII processing schema into analysis findings."""
    findings: list[dict[str, object]] = []

    for entity in legacy_result.entities:
        categories = [
            category.value if hasattr(category, "value") else str(category)
            for category in entity.categories
        ]
        sources = [
            source.value if hasattr(source, "value") else str(source)
            for source in entity.sources
        ]
        timestamps = [
            value
            for value in [entity.first_observed, entity.last_updated]
            if value
        ]

        supporting_data: dict[str, list[str]] = {
            "entities": [entity.name],
            "categories": categories,
            "sources": sources,
            "tags": list(entity.tags),
        }
        if timestamps:
            supporting_data["timestamps"] = timestamps

        findings.append(
            {
                "id": entity.id,
                "title": entity.name,
                "finding": entity.description,
                "evidence_summary": (
                    f"Observed in categories {', '.join(categories) or 'unknown'} "
                    f"from sources {', '.join(sources) or 'unknown'}."
                ),
                "source": sources[0] if sources else "manual",
                "confidence": entity.confidence,
                "relevant_to": list(entity.relevant_to),
                "supporting_data": supporting_data,
                "why_it_matters": (
                    f"This entity contributes to PIRs {', '.join(entity.relevant_to)}."
                    if entity.relevant_to
                    else "This entity contributes to the overall assessment."
                ),
                "uncertainties": [],
            }
        )

    return ProcessingResult(findings=findings, gaps=list(legacy_result.gaps))


class ProcessingPrototypeService:
    """Loads a processing result from a session's processed.json."""

    def get_processing_result(self, session_id: str) -> ProcessingResult:
        """Load and validate the session processing result."""
        processed_path = _SESSIONS_DATA_DIR / session_id / "processed.json"
        result = self._try_load_session(processed_path)
        if result is None:
            raise ValueError(PROCESSING_RESULT_UNAVAILABLE_MESSAGE)

        logger.info(
            "Loaded processing result from session %s processed.json", session_id
        )
        return result

    def _try_load_session(self, processed_path: Path) -> ProcessingResult | None:
        """Try to load a ProcessingResult from a session processed.json file."""
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

        for attempt in reversed(attempts):
            if not isinstance(attempt, str):
                continue
            result = _try_parse_processing_result(attempt)
            if result is not None:
                return result

        logger.info("No valid ProcessingResult found in %s attempts", len(attempts))
        return None
