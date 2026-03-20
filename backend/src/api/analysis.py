"""API router for prototype analysis endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from src.models.analysis import AnalysisDraft, CouncilNote, ProcessingResult
from src.services.analysis_prototype_service import AnalysisPrototypeService
from src.services.analysis_session_store import AnalysisSessionStore
from src.services.council_service import CouncilService
from src.services.processing_prototype_service import ProcessingPrototypeService
from src.services.reasearch_logger import ResearchLogger

router = APIRouter(prefix="/api/analysis")


class AnalysisDraftRequest(BaseModel):
    """Request body for generating a prototype analysis draft."""

    session_id: str = Field(..., min_length=1)
    force_refresh: bool = False


class AnalysisDraftResponse(BaseModel):
    """Response body containing both processing and analysis prototype data."""

    processing_result: ProcessingResult
    analysis_draft: AnalysisDraft
    latest_council_note: CouncilNote | None = None


class AnalysisCouncilRequest(BaseModel):
    """Request body for running an analysis-stage council deliberation."""

    session_id: str = Field(..., min_length=1)
    debate_point: str = ""
    finding_ids: list[str] = Field(default_factory=list)
    selected_perspectives: list[str] = Field(..., min_length=2)

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


async def _build_draft(
    session_id: str,
    store: AnalysisSessionStore,
    force_refresh: bool = False,
    processing_service: ProcessingPrototypeService | None = None,
    analysis_service: AnalysisPrototypeService | None = None,
) -> AnalysisDraftResponse:
    processing_service = processing_service or ProcessingPrototypeService()
    analysis_service = analysis_service or AnalysisPrototypeService()

    state = store.get_or_create(session_id)
    if force_refresh or state.processing_result is None or state.analysis_draft is None:
        processing_result = processing_service.get_processing_result(session_id)
        analysis_draft = await analysis_service.generate_draft(processing_result)
        if force_refresh:
            state.session_id = session_id
            state.processing_result = processing_result
            state.analysis_draft = analysis_draft
            state.latest_council_note = None
            state = store.save(state)
        else:
            state = store.save_draft(session_id, processing_result, analysis_draft)

    return AnalysisDraftResponse(
        processing_result=state.processing_result,
        analysis_draft=state.analysis_draft,
        latest_council_note=state.latest_council_note,
    )


@router.post("/draft", response_model=AnalysisDraftResponse)
async def create_analysis_draft(
    request: AnalysisDraftRequest,
) -> AnalysisDraftResponse:
    """Load the prototype processing result and generate a draft analysis."""
    store = AnalysisSessionStore()

    try:
        return await _build_draft(
            request.session_id,
            store,
            force_refresh=request.force_refresh,
        )
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/council", response_model=CouncilNote)
async def create_analysis_council(
    request: AnalysisCouncilRequest,
) -> CouncilNote:
    """Run a council deliberation against the current analysis-stage state."""
    store = AnalysisSessionStore()
    council_service = CouncilService()
    research_logger = ResearchLogger(session_id=request.session_id)

    try:
        draft_response = await _build_draft(request.session_id, store)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

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
            detail=(
                "Unknown finding_ids: " + ", ".join(invalid_finding_ids)
            ),
        )

    try:
        council_note = await council_service.run_council(
            session_id=request.session_id,
            debate_point=request.debate_point,
            selected_perspectives=request.selected_perspectives,
            processing_result=draft_response.processing_result,
            analysis_draft=draft_response.analysis_draft,
            finding_ids=request.finding_ids or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        store.save_council_note(request.session_id, council_note)
        research_logger.create_log(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "phase": "analysis_council",
                "session_id": request.session_id,
                "debate_point": request.debate_point,
                "selected_perspectives": request.selected_perspectives,
                "finding_ids": request.finding_ids,
                "transcript_path": council_note.transcript_path,
                "council_summary": council_note.summary,
            }
        )
        return council_note
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
