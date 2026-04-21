"""Loads processing results from session storage.

Reads from the processing_attempts table in sessions.db.
Falls back to the legacy processed.json files if DB load fails.
"""

import json
import logging
import re
from pathlib import Path

from pydantic import ValidationError

from src.models.analysis import ProcessingResult
from src.models.processing import ProcessingResult as LegacyProcessingResult

logger = logging.getLogger(__name__)

# Legacy fallback path — kept for pre-migration data
_SESSIONS_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "sessions"
PROCESSING_RESULT_UNAVAILABLE_MESSAGE = (
    "No processed result available for this session. Complete processing first."
)


def _try_parse_processing_result(raw: str) -> ProcessingResult | None:
    """Attempt to extract a ProcessingResult from raw LLM output."""
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
    candidate = match.group(1) if match else raw.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s*```$", "", candidate).strip()

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

    if "pmesii_entities" in payload:
        return _convert_grouped_pmesii_result(payload)

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
            value for value in [entity.first_observed, entity.last_updated] if value
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

    return ProcessingResult(findings=findings, gaps=list(legacy_result.gaps))  # type: ignore[arg-type]


def _convert_grouped_pmesii_result(payload: dict) -> ProcessingResult | None:
    """Convert grouped PMESII output from older processing runs."""
    grouped = payload.get("pmesii_entities")
    if not isinstance(grouped, dict):
        return None

    findings: list[dict[str, object]] = []
    finding_index = 1
    for category, items in grouped.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            text = str(item.get("entity") or item.get("description") or "").strip()
            if not text:
                continue
            source = str(item.get("source") or "unknown")
            resource_id = str(item.get("resource_id") or "").strip()
            supporting_data: dict[str, list[str]] = {
                "categories": [str(category)],
                "sources": [source],
            }
            if resource_id:
                supporting_data["source_refs"] = [resource_id]

            findings.append(
                {
                    "id": f"F-{finding_index:02d}",
                    "title": text[:80],
                    "finding": text,
                    "evidence_summary": (
                        f"Extracted from {source}"
                        + (f" resource {resource_id}." if resource_id else ".")
                    ),
                    "source": source,
                    "confidence": 70,
                    "relevant_to": [],
                    "supporting_data": supporting_data,
                    "why_it_matters": (
                        f"This {category} factor contributes to the overall assessment."
                    ),
                    "uncertainties": [],
                }
            )
            finding_index += 1

    if not findings:
        return None

    gaps = payload.get("gaps")
    return ProcessingResult(
        findings=findings,  # type: ignore[arg-type]
        gaps=[str(gap) for gap in gaps] if isinstance(gaps, list) else [],
    )


class ProcessingResultStore:
    """Loads a processing result from the processing_attempts DB table."""

    def __init__(self, uow=None):
        self._uow = uow

    async def get_processing_result(self, session_id: str) -> ProcessingResult:
        """Load and validate the session processing result from DB (or legacy JSON)."""
        # Try DB first
        if self._uow:
            result = await self._try_load_from_db(session_id)
            if result is not None:
                logger.info(
                    "Loaded processing result from processing_attempts table for session %s",
                    session_id,
                )
                return result

        # Legacy fallback: JSON file
        processed_path = _SESSIONS_DATA_DIR / session_id / "processed.json"
        result = self._try_load_session(processed_path)
        if result is not None:
            logger.info(
                "Loaded processing result from legacy processed.json for session %s",
                session_id,
            )
            return result

        raise ValueError(PROCESSING_RESULT_UNAVAILABLE_MESSAGE)

    async def _try_load_from_db(self, session_id: str) -> ProcessingResult | None:
        """Read processing attempts from DB, return the latest valid ProcessingResult."""
        try:
            attempts = await self._uow.processing_attempts.get_all(session_id)
        except Exception:
            logger.exception(
                "DB load failed for session %s processing attempts", session_id
            )
            return None

        if not attempts:
            return None

        # Walk attempts newest-first to find the most recent valid result
        for attempt in reversed(attempts):
            result = _try_parse_processing_result(attempt.raw_result)
            if result is not None:
                return result

        logger.info(
            "No valid ProcessingResult found in %d DB attempts for session %s",
            len(attempts),
            session_id,
        )
        return None

    def _try_load_session(self, processed_path: Path) -> ProcessingResult | None:
        """Try to load a ProcessingResult from a legacy processed.json file."""
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
