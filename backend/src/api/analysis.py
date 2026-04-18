"""API router for analysis endpoints."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from src.db.unit_of_work import UnitOfWork, get_uow
from src.mcp_client.client import MCPClient
from src.models.analysis import (
    AnalysisDraft,
    CouncilNote,
    CouncilRunSettings,
    ProcessingResult,
)
from src.models.confidence import CollectionCoverageResult
from src.services.analysis_service import AnalysisService
from src.services.analysis_session_store import AnalysisSessionStore
from src.services.confidence.collection_coverage import compute_collection_coverage
from src.services.council_service import CouncilService
from src.services.processing_result_store import (
    PROCESSING_RESULT_UNAVAILABLE_MESSAGE,
    ProcessingResultStore,
)
from src.services.reasearch_logger import ResearchLogger


def _get_mcp_client() -> MCPClient:
    return MCPClient()


logger = logging.getLogger(__name__)

_SESSIONS_DIR = Path(__file__).resolve().parents[2] / "sessions"

router = APIRouter(prefix="/api/analysis")


class AnalysisDraftRequest(BaseModel):
    """Request body for generating an analysis draft."""

    session_id: str = Field(..., min_length=1)
    force_refresh: bool = False


async def _load_pirs_for_session(
    session_id: str, uow: UnitOfWork | None = None
) -> list[dict]:
    """Load the approved PIR list from sessions.db or legacy JSON.

    Returns an empty list if the session is missing or malformed — coverage
    will still compute (all PIRs will be LOW), so callers never crash.
    """
    # Try DB first
    if uow:
        try:
            row = await uow.sessions.get(session_id)
            if row and row.current_pir:
                pir_data = json.loads(row.current_pir)
                pirs: list[dict] = pir_data.get("pirs", [])
                return [p for p in pirs if isinstance(p, dict) and "question" in p]
        except Exception:
            logger.debug("DB PIR load failed for %s, trying file fallback", session_id)

    # Legacy file fallback
    session_path = _SESSIONS_DIR / f"{session_id}.json"
    if not session_path.exists():
        logger.debug("Session file not found for PIR loading: %s", session_path)
        return []
    try:
        data = json.loads(session_path.read_text(encoding="utf-8"))
        current_pir_raw = data.get("direction_flow", {}).get("current_pir")
        if not current_pir_raw:
            return []
        pir_data = json.loads(current_pir_raw)
        pirs = pir_data.get("pirs", [])
        return [p for p in pirs if isinstance(p, dict) and "question" in p]
    except (OSError, json.JSONDecodeError, AttributeError):
        logger.warning("Failed to load PIRs from session %s", session_id)
        return []


class AnalysisDraftResponse(BaseModel):
    """Response body containing processing and analysis data."""

    processing_result: ProcessingResult
    analysis_draft: AnalysisDraft
    latest_council_note: CouncilNote | None = None
    collection_coverage: CollectionCoverageResult | None = None
    data_source: Literal["session"] = "session"


class AnalysisCouncilRequest(BaseModel):
    """Request body for running an analysis-stage council deliberation."""

    session_id: str = Field(..., min_length=1)
    debate_point: str = ""
    finding_ids: list[str] = Field(default_factory=list)
    selected_perspectives: list[str] = Field(..., min_length=2)
    council_settings: CouncilRunSettings | None = None

    @field_validator("debate_point")
    @classmethod
    def _strip_debate_point(cls, value: str) -> str:
        return value.strip()

    @field_validator("finding_ids")
    @classmethod
    def _normalize_finding_ids(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            cleaned = item.strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)
        return normalized

    @field_validator("selected_perspectives")
    @classmethod
    def _normalize_perspectives(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            cleaned = item.strip().lower()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)
        return normalized

    @model_validator(mode="after")
    def _validate_inputs(self) -> "AnalysisCouncilRequest":
        if len(self.selected_perspectives) < 2:
            raise ValueError("selected_perspectives must contain at least 2 items")
        if not self.debate_point and not self.finding_ids:
            raise ValueError(
                "debate_point may be empty only when finding_ids are provided"
            )
        return self


async def _load_selected_perspectives(
    session_id: str, uow: UnitOfWork | None
) -> list[str] | None:
    """Load selected perspectives from the session's direction context."""
    if not uow:
        return None
    try:
        row = await uow.sessions.get(session_id)
        if row and row.direction_context:
            ctx = json.loads(row.direction_context)
            raw = ctx.get("perspectives") or []
            return [p.lower() for p in raw if isinstance(p, str) and p] or None
    except Exception:
        logger.debug("Failed to load perspectives for session %s", session_id)
    return None


async def _build_draft(
    session_id: str,
    store: AnalysisSessionStore,
    uow: UnitOfWork | None = None,
    force_refresh: bool = False,
    processing_service: ProcessingResultStore | None = None,
    analysis_service: AnalysisService | None = None,
    mcp_client: MCPClient | None = None,
) -> AnalysisDraftResponse:
    processing_service = processing_service or ProcessingResultStore(uow=uow)
    analysis_service = analysis_service or AnalysisService(mcp_client or MCPClient())

    state = await store.get_or_create(session_id)
    processing_result = await processing_service.get_processing_result(session_id)
    processing_changed = state.processing_result != processing_result

    if (
        force_refresh
        or state.processing_result is None
        or state.analysis_draft is None
        or processing_changed
    ):
        selected_perspectives = await _load_selected_perspectives(session_id, uow)
        draft_result = await analysis_service.generate_draft(
            processing_result,
            selected_perspectives=selected_perspectives,
        )
        if isinstance(draft_result, tuple):
            analysis_draft, enriched_processing_result = draft_result
        else:
            analysis_draft = draft_result
            enriched_processing_result = processing_result
        if force_refresh or processing_changed:
            state.session_id = session_id
            state.processing_result = enriched_processing_result
            state.analysis_draft = analysis_draft
            state.latest_council_note = None
            state = await store.save(state)
        else:
            state = await store.save_draft(
                session_id, enriched_processing_result, analysis_draft
            )
        processing_result = enriched_processing_result

    assert state.processing_result is not None and state.analysis_draft is not None
    pirs = await _load_pirs_for_session(session_id, uow=uow)
    coverage = compute_collection_coverage(
        findings=processing_result.findings,
        gaps=processing_result.gaps,
        pirs=pirs,
    )

    return AnalysisDraftResponse(
        processing_result=state.processing_result,
        analysis_draft=state.analysis_draft,
        latest_council_note=state.latest_council_note,
        collection_coverage=coverage,
        data_source="session",
    )


@router.post("/draft", response_model=AnalysisDraftResponse)
async def create_analysis_draft(
    request: AnalysisDraftRequest,
    uow: UnitOfWork = Depends(get_uow),
    mcp_client: MCPClient = Depends(_get_mcp_client),
) -> AnalysisDraftResponse:
    """Load the processing result and generate a draft analysis."""
    store = AnalysisSessionStore(uow=uow)

    try:
        return await _build_draft(
            request.session_id,
            store,
            uow=uow,
            force_refresh=request.force_refresh,
            mcp_client=mcp_client,
        )
    except ValueError as exc:
        status_code = 409 if str(exc) == PROCESSING_RESULT_UNAVAILABLE_MESSAGE else 500
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post("/council", response_model=CouncilNote)
async def create_analysis_council(
    request: AnalysisCouncilRequest,
    uow: UnitOfWork = Depends(get_uow),
    mcp_client: MCPClient = Depends(_get_mcp_client),
) -> CouncilNote:
    """Run a council deliberation against the current analysis-stage state."""
    store = AnalysisSessionStore(uow=uow)
    council_service = CouncilService()
    research_logger = ResearchLogger(session_id=request.session_id)

    try:
        draft_response = await _build_draft(
            request.session_id,
            store,
            uow=uow,
            mcp_client=mcp_client,
        )
    except ValueError as exc:
        status_code = 409 if str(exc) == PROCESSING_RESULT_UNAVAILABLE_MESSAGE else 500
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    available_finding_ids = {
        finding.id for finding in draft_response.processing_result.findings
    }
    invalid_finding_ids = [
        finding_id
        for finding_id in request.finding_ids
        if finding_id not in available_finding_ids
    ]
    if invalid_finding_ids:
        raise HTTPException(
            status_code=400,
            detail=("Unknown finding_ids: " + ", ".join(invalid_finding_ids)),
        )

    try:
        council_note = await council_service.run_council(
            session_id=request.session_id,
            debate_point=request.debate_point,
            selected_perspectives=request.selected_perspectives,
            processing_result=draft_response.processing_result,
            analysis_draft=draft_response.analysis_draft,
            finding_ids=request.finding_ids or None,
            council_settings=request.council_settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        await store.save_council_note(request.session_id, council_note)
        research_logger.create_log(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "phase": "analysis_council",
                "session_id": request.session_id,
                "debate_point": request.debate_point,
                "selected_perspectives": request.selected_perspectives,
                "finding_ids": request.finding_ids,
                "council_settings": (
                    request.council_settings.model_dump()
                    if request.council_settings
                    else None
                ),
                "transcript_path": council_note.transcript_path,
                "council_summary": council_note.summary,
            }
        )
        return council_note
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
