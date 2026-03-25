"""Persistence for analysis-stage draft and council session state."""

import json
from pathlib import Path

from pydantic import ValidationError

from src.models.analysis import AnalysisSessionState, AnalysisDraft, CouncilNote, ProcessingResult


class AnalysisSessionStore:
    """Persist and reload analysis-stage state across refresh/reload."""

    def __init__(self, sessions_dir: str | Path | None = None):
        if sessions_dir is None:
            sessions_dir = Path(__file__).resolve().parents[2] / "sessions"
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.analysis.json"

    def load(self, session_id: str) -> AnalysisSessionState | None:
        path = self._session_path(session_id)
        if not path.exists():
            return None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return AnalysisSessionState.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"Failed to load analysis session state for {session_id}") from exc

    def save(self, state: AnalysisSessionState) -> AnalysisSessionState:
        path = self._session_path(state.session_id)
        try:
            path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"Failed to save analysis session state for {state.session_id}") from exc
        return state

    def get_or_create(self, session_id: str) -> AnalysisSessionState:
        state = self.load(session_id)
        if state is not None:
            return state
        return AnalysisSessionState(session_id=session_id)

    def save_draft(
        self,
        session_id: str,
        processing_result: ProcessingResult,
        analysis_draft: AnalysisDraft,
    ) -> AnalysisSessionState:
        state = self.get_or_create(session_id)
        state.processing_result = processing_result
        state.analysis_draft = analysis_draft
        return self.save(state)

    def save_council_note(
        self,
        session_id: str,
        council_note: CouncilNote,
    ) -> AnalysisSessionState:
        state = self.get_or_create(session_id)
        state.latest_council_note = council_note
        return self.save(state)
