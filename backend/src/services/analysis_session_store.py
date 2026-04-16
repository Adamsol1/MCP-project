"""Persistence for analysis-stage draft and council session state.

Uses analysis_sessions table in sessions.db via the AnalysisSessionRepository.
Falls back to JSON file persistence if no UoW is provided.
"""

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from src.models.analysis import AnalysisSessionState, AnalysisDraft, CouncilNote, ProcessingResult

logger = logging.getLogger("app")


class AnalysisSessionStore:
    """Persist and reload analysis-stage state across refresh/reload."""

    def __init__(self, uow=None, sessions_dir: str | Path | None = None):
        self._uow = uow
        # Legacy fallback path
        if sessions_dir is None:
            sessions_dir = Path(__file__).resolve().parents[2] / "sessions"
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.analysis.json"

    async def load(self, session_id: str) -> AnalysisSessionState | None:
        # Try DB first
        if self._uow:
            try:
                row = await self._uow.analysis_sessions.get_by_session(session_id)
                if row is None:
                    return None
                return AnalysisSessionState(
                    session_id=session_id,
                    processing_result=(
                        ProcessingResult.model_validate(json.loads(row.processing_result))
                        if row.processing_result else None
                    ),
                    analysis_draft=(
                        AnalysisDraft.model_validate(json.loads(row.analysis_draft))
                        if row.analysis_draft else None
                    ),
                    latest_council_note=(
                        CouncilNote.model_validate(json.loads(row.latest_council_note))
                        if row.latest_council_note else None
                    ),
                )
            except Exception:
                logger.exception(f"[AnalysisSessionStore] DB load failed for {session_id}, trying file fallback")

        # Legacy file fallback
        path = self._session_path(session_id)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return AnalysisSessionState.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"Failed to load analysis session state for {session_id}") from exc

    async def save(self, state: AnalysisSessionState) -> AnalysisSessionState:
        # Try DB first
        if self._uow:
            try:
                row = await self._uow.analysis_sessions.get_or_create(state.session_id)
                row.processing_result = (
                    state.processing_result.model_dump_json() if state.processing_result else None
                )
                row.analysis_draft = (
                    state.analysis_draft.model_dump_json() if state.analysis_draft else None
                )
                row.latest_council_note = (
                    state.latest_council_note.model_dump_json() if state.latest_council_note else None
                )
                await self._uow.analysis_sessions.update(row)
                await self._uow.commit()
                return state
            except Exception:
                logger.exception(f"[AnalysisSessionStore] DB save failed for {state.session_id}, trying file fallback")

        # Legacy file fallback
        path = self._session_path(state.session_id)
        try:
            path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"Failed to save analysis session state for {state.session_id}") from exc
        return state

    async def get_or_create(self, session_id: str) -> AnalysisSessionState:
        state = await self.load(session_id)
        if state is not None:
            return state
        return AnalysisSessionState(session_id=session_id)

    async def save_draft(
        self,
        session_id: str,
        processing_result: ProcessingResult,
        analysis_draft: AnalysisDraft,
    ) -> AnalysisSessionState:
        state = await self.get_or_create(session_id)
        state.processing_result = processing_result
        state.analysis_draft = analysis_draft
        return await self.save(state)

    async def save_council_note(
        self,
        session_id: str,
        council_note: CouncilNote,
    ) -> AnalysisSessionState:
        state = await self.get_or_create(session_id)
        state.latest_council_note = council_note
        return await self.save(state)
