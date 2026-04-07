"""Prototype service for loading processing results from placeholder JSON files."""

import json
import re
from pathlib import Path

from pydantic import ValidationError

from src.models.analysis import ProcessingResult


class ProcessingPrototypeService:
    """Loads a prototype processing result from disk."""

    DEFAULT_DATASET = "demo_processing_result"
    DATASET_PATTERN = re.compile(r"^demo_processing_result(?:_\d+)?$")

    def __init__(
        self,
        prototype_path: str | Path | None = None,
        dataset_name: str | None = None,
    ):
        if prototype_path is None:
            prototype_path = self._resolve_dataset_path(
                dataset_name or self.DEFAULT_DATASET
            )
        self.prototype_path = Path(prototype_path)

    @classmethod
    def _outputs_dir(cls) -> Path:
        return Path(__file__).resolve().parents[2] / "data" / "outputs"

    @classmethod
    def _normalize_dataset_name(cls, dataset_name: str) -> str:
        cleaned = dataset_name.strip()
        if cleaned.endswith(".json"):
            cleaned = cleaned[:-5]

        if not cls.DATASET_PATTERN.fullmatch(cleaned):
            raise ValueError(f"Unknown demo dataset '{dataset_name}'")

        return cleaned

    @classmethod
    def _resolve_dataset_path(cls, dataset_name: str) -> Path:
        normalized_name = cls._normalize_dataset_name(dataset_name)
        path = cls._outputs_dir() / f"{normalized_name}.json"
        if not path.exists():
            raise ValueError(f"Unknown demo dataset '{dataset_name}'")
        return path

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
