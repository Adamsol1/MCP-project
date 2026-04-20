"""
API router for the dialogue flow.

Handles incoming messages from the frontend, routes them through
the dialogue state machine (DirectionFlow), and returns structured responses.

Sessions are cached in memory in `_sessions` and persisted to sessions.db.
"""

import asyncio
import json
import logging
import os
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.db.mappers import row_to_session, session_to_row
from src.db.unit_of_work import UnitOfWork, get_uow
from src.mcp_client.client import MCPClient
from src.models.analysis import CouncilRunSettings
from src.models.dialogue import DialogueAction, DialogueResponse, Phase
from src.services.ai_orchestrator import AIOrchestrator
from src.services.analysis_service import AnalysisService
from src.services.analysis_session_store import AnalysisSessionStore
from src.services.collection_service import CollectionService
from src.services.collection_status import CollectionStatusTracker
from src.services.council_service import CouncilService
from src.services.dialogue_service import DialogueService
from src.services.llm_service import LLMService
from src.services.processing_result_store import ProcessingResultStore
from src.services.processing_service import ProcessingService
from src.services.reasearch_logger import ResearchLogger
from src.services.review_service import ReviewService
from src.services.state_machines.analysis_flow import AnalysisFlow, AnalysisState
from src.services.state_machines.collection_flow import CollectionFlow, CollectionState
from src.services.state_machines.council_flow import CouncilFlow
from src.services.state_machines.direction_flow import DirectionFlow, DirectionState
from src.services.state_machines.processing_flow import ProcessingFlow, ProcessingState

# Global values used in the file
_REVIEW_MCP_URL = os.getenv("REVIEW_MCP_URL", "http://127.0.0.1:8002/sse")
DEV_TOOLS_ENABLED = os.getenv("DEV_TOOLS_ENABLED", "true").lower() == "true"

_GEMINI_MODEL = "gemini-2.5-flash"
_GATHER_MORE_CONTENT = (
    "What gaps would you like to fill? Describe what additional information to gather."
)
_SUB_STATE_GATHER_MORE = "awaiting_gather_more"
_SUB_STATE_AWAITING_DECISION = "awaiting_decision"
_DEFAULT_DIALOGUE_REQUEST_TIMEOUT_SECONDS = 600.0

router = APIRouter(prefix="/api/dialogue")
logger = logging.getLogger("app")

# Legacy filesystem paths — kept for dev-tool snapshot/restore endpoints only.
# The main session save/load path uses sessions.db via UnitOfWork (see _save_session/_load_session).
_SESSIONS_DIR = Path(__file__).parent.parent.parent / "sessions"
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_DATA_DIR = _BACKEND_DIR / "data"
_SESSION_DATA_DIR = _DATA_DIR / "sessions"
_OUTPUTS_DIR = _DATA_DIR / "outputs"
_COLLECTION_STATUS_DIR = _DATA_DIR / "collection_status"
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _dialogue_request_timeout_seconds(request: Any) -> float:
    raw_timeout = os.getenv("DIALOGUE_REQUEST_TIMEOUT_SECONDS")
    try:
        timeout = (
            float(raw_timeout)
            if raw_timeout is not None
            else _DEFAULT_DIALOGUE_REQUEST_TIMEOUT_SECONDS
        )
    except ValueError:
        timeout = _DEFAULT_DIALOGUE_REQUEST_TIMEOUT_SECONDS

    if request.council_settings is not None:
        council_timeout = (
            request.council_settings.timeout_seconds
            * max(1, request.council_settings.rounds)
            + 60
        )
        timeout = max(timeout, float(council_timeout))

    return max(30.0, timeout)


def ensure_sessions_dir() -> None:
    _SESSIONS_DIR.mkdir(exist_ok=True)


class IntelligenceSession:
    """
    Holds all phase flows for a single intelligence session.
    The session is created upon session start, and will be continously written to disk by each state.

    Args:
        Session_id : Identifer of the session
        research_logger: Logger for this session


    """

    def __init__(self, session_id: str, research_logger: ResearchLogger):
        self.session_id = session_id
        self.research_logger = research_logger
        self.direction_flow = DirectionFlow(
            session_id=session_id, research_logger=research_logger
        )
        self.collection_flow: CollectionFlow | None = None
        self.processing_flow: ProcessingFlow | None = None
        self.analysis_flow: AnalysisFlow | None = None
        self.council_flow: CouncilFlow | None = None


_sessions: dict[str, IntelligenceSession] = {}


async def _save_session(session: IntelligenceSession, uow: UnitOfWork) -> None:
    """Persist session state to sessions.db so it survives server restarts.

    Args:
        session: The active session to save
        uow: Unit of Work with an open DB transaction
    """
    row = session_to_row(session)
    await uow.sessions.upsert(row)
    await uow.commit()


async def _load_session(
    session_id: str, research_logger, uow: UnitOfWork
) -> IntelligenceSession | None:
    """Load a previously persisted session from sessions.db.

    Returns None if not found.
    """
    row = await uow.sessions.get(session_id)
    if row is None:
        return None

    session = row_to_session(row, research_logger)
    logger.info(f"[Session {session_id}] Restored from DB")
    return session  # type: ignore[no-any-return]


# Request model
class DialogueMessageRequest(BaseModel):
    """
    Incoming request body for the /message endpoint
    """

    message: str
    session_id: str
    perspectives: list[str] = ["NEUTRAL"]
    approved: bool | None = None
    language: str = "en"
    """BCP-47 language code from the user's settings (e.g. 'en', 'no').
    Forwarded to MCP tools so the ai generates responses in the correct language."""
    settings_timeframe: str = ""
    """Timeframe pre-set by the user in Settings → Parameters (e.g. 'Last 30 days').
    When non-empty and the session context has no timeframe yet, the backend pre-fills
    context.timeframe so the AI skips the timeframe clarifying question."""
    selected_sources: list[str] = []
    """Sources selected by the user in the collection phase."""
    gather_more: bool = False
    """True when the user wants to gather more data instead of approving the collection."""
    council_debate_point: str = ""
    """Debate point entered by the user when triggering a council run."""
    council_finding_ids: list[str] = []
    """Finding IDs selected by the user to scope the council deliberation."""
    council_perspectives: list[str] = []
    """Perspectives selected for the council run. Falls back to session perspectives if empty."""
    council_settings: CouncilRunSettings | None = None
    """Runtime settings for the council run (mode, rounds, timeout, vote retry)."""


# Response Model
class DialogueMessageResponse(BaseModel):
    """
    Outgoing repsonse for the /message endpoint
    """

    question: str
    action: DialogueAction
    stage: str
    phase: str
    sub_state: str | None = None
    review_activity: list[dict] | None = None


class DialogueDevStateResponse(BaseModel):
    session_id: str
    stage: str
    phase: str
    sub_state: str | None = None
    question_count: int
    max_questions: int
    missing_context_fields: list[str]
    has_sufficient_context: bool
    awaiting_user_decision: bool
    has_modifications: bool


class DialogueDevStateRequest(BaseModel):
    session_id: str
    stage: str
    sub_state: str | None = None
    seed_context: dict[str, Any] | None = None
    current_pir: str | None = None


class DialogueDevSnapshot(BaseModel):
    session_id: str
    title: str
    stage: str
    phase: str
    updated_at: str | None = None
    artifacts: dict[str, bool]


class DialogueDevRestoreRequest(BaseModel):
    source_session_id: str
    target_session_id: str
    target_stage: str | None = None
    target_phase: str | None = None


class DialogueDevRestoreResponse(DialogueDevStateResponse):
    source_session_id: str
    messages: list[dict[str, Any]]


async def evict_session(session_id: str, uow: UnitOfWork) -> None:
    """Remove a session from the in-memory cache and delete it from the DB.

    Args:
        session_id: session identifier
        uow: Unit of Work with an open DB transaction
    """
    _sessions.pop(session_id, None)
    await uow.sessions.delete_cascade(session_id)
    await uow.commit()
    logger.info(f"[Session {session_id}] Evicted from cache and DB")


def _normalize_dialogue_action(action: DialogueAction | str) -> DialogueAction:
    """
    Create a string og enum to a DialogueAction
    This is needed as return values from state machien can be both strings or finished enums

    Args:
        Dialogueaction enum og string

    Retruns:
        The dialogueaction enum

    Raises:
        Valuerror if string does not match legal action
    """

    if isinstance(action, DialogueAction):
        return action
    try:
        return DialogueAction(action)
    except ValueError as exc:
        raise ValueError(f"Unsupported dialogue action: {action}") from exc


def _convert_to_message_response(
    response: DialogueResponse,
    stage: str,
    phase: Phase,
    sub_state: str | None = None,
) -> DialogueMessageResponse:
    """
    Converts internal DialogueRespone to the API respone format

    Args:
        Response: reponse object from state machine
        Stage: current state machine phase
        sub_state_ optional stage information

    Returns:
        DialoguemessageResponse that can be sent to frontend

    Raises:
        Httpexceptin 500 if recieved response contains illegal action

    Example:
        Input:  DialogueResponse(action="ask_question", content="What is the scope?")
        Output: DialogueMessageResponse(question="What is the scope?", action="ask_question")



    """
    try:
        action = _normalize_dialogue_action(response.action)
    except ValueError as exc:
        logger.error("Failed to convert dialogue response action: %s", exc)
        raise HTTPException(
            status_code=500, detail="Internal error: invalid dialogue action"
        ) from exc

    result = DialogueMessageResponse(
        question=response.content,
        action=action,
        stage=stage,
        phase=phase.value,
        sub_state=sub_state,
        review_activity=(
            [item.model_dump() for item in response.review_activity]
            if response.review_activity
            else None
        ),
    )
    return result


# Temp
def _ensure_dev_tools_enabled():
    if not DEV_TOOLS_ENABLED:
        raise HTTPException(status_code=404, detail="Not found")


async def _get_or_create_session(
    session_id: str, uow: UnitOfWork
) -> IntelligenceSession:
    """Get or create session. Checks in-memory cache first, then DB, else creates new.

    Args:
        session_id: Unique identifier of session
        uow: Unit of Work with an open DB transaction

    Returns:
        the retrieved or new IntelligenceSession
    """
    if session_id not in _sessions:
        research_logger = ResearchLogger(session_id=session_id)
        loaded = await _load_session(session_id, research_logger, uow)
        if loaded:
            _sessions[session_id] = loaded
        else:
            logger.info(f"[Session {session_id}] Creating new session")
            _sessions[session_id] = IntelligenceSession(session_id, research_logger)
    return _sessions[session_id]


def _get_active_stage_and_phase(session: IntelligenceSession) -> tuple[str, Phase]:
    if session.analysis_flow:
        return session.analysis_flow.state.value, Phase.ANALYSIS
    if session.processing_flow:
        return session.processing_flow.state.value, Phase.PROCESSING
    if session.collection_flow:
        return session.collection_flow.state.value, Phase.COLLECTION
    return session.direction_flow.state.value, Phase.DIRECTION


def _build_dev_state_response(
    session_id: str, session: IntelligenceSession
) -> DialogueDevStateResponse:
    active_stage, active_phase = _get_active_stage_and_phase(session)
    state = session.direction_flow.get_debug_state()
    sub_state = (
        state["sub_state"]
        if active_phase == Phase.DIRECTION
        else _default_dev_sub_state(active_stage)
    )
    return DialogueDevStateResponse(
        session_id=session_id,
        stage=active_stage,
        phase=active_phase.value,
        sub_state=sub_state,
        question_count=state["question_count"],
        max_questions=state["max_questions"],
        missing_context_fields=state["missing_context_fields"],
        has_sufficient_context=state["has_sufficient_context"],
        awaiting_user_decision=state["awaiting_user_decision"],
        has_modifications=state["has_modifications"],
    )


def _default_dev_sub_state(stage: str) -> str | None:
    if stage in {
        DirectionState.SUMMARY_CONFIRMING.value,
        DirectionState.PIR_CONFIRMING.value,
        CollectionState.PLAN_CONFIRMING.value,
        CollectionState.REVIEWING.value,
        ProcessingState.PROCESSING.value,
        ProcessingState.REVIEWING.value,
    }:
        return _SUB_STATE_AWAITING_DECISION
    return None


def _validate_dev_session_id(session_id: str) -> str:
    if not _SESSION_ID_RE.fullmatch(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id")
    return session_id


def _safe_child(root: Path, *parts: str) -> Path:
    root_resolved = root.resolve()
    path = root_resolved.joinpath(*parts).resolve()
    if path != root_resolved and root_resolved not in path.parents:
        raise HTTPException(status_code=400, detail="Invalid artifact path")
    return path


def _read_json_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _latest_mtime(paths: list[Path]) -> str | None:
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    return datetime.fromtimestamp(
        max(path.stat().st_mtime for path in existing), tz=UTC
    ).isoformat()


def _session_artifact_paths(session_id: str) -> dict[str, Path]:
    return {
        "session": _safe_child(_SESSIONS_DIR, f"{session_id}.json"),
        "analysis": _safe_child(_SESSIONS_DIR, f"{session_id}.analysis.json"),
        "data": _safe_child(_SESSION_DATA_DIR, session_id),
        "collection_status": _safe_child(_COLLECTION_STATUS_DIR, f"{session_id}.json"),
        "research_log": _safe_child(_OUTPUTS_DIR, f"research_log_{session_id}.jsonl"),
        "reasoning_log": _safe_child(_OUTPUTS_DIR, f"reasoning_log_{session_id}.json"),
    }


def _snapshot_title(session_id: str, session_data: dict[str, Any] | None) -> str:
    context = (session_data or {}).get("direction_flow", {}).get("context", {})
    initial_query = context.get("initial_query")
    if isinstance(initial_query, str) and initial_query.strip():
        return initial_query.strip()[:90]
    return session_id


def _stage_phase_from_session_data(
    session_data: dict[str, Any] | None,
) -> tuple[str, str]:
    if not session_data:
        return DirectionState.INITIAL.value, Phase.DIRECTION.value
    analysis_flow = session_data.get("analysis_flow")
    if isinstance(analysis_flow, dict) and analysis_flow.get("state"):
        return str(analysis_flow["state"]), Phase.ANALYSIS.value
    processing_flow = session_data.get("processing_flow")
    if isinstance(processing_flow, dict) and processing_flow.get("state"):
        return str(processing_flow["state"]), Phase.PROCESSING.value
    collection_flow = session_data.get("collection_flow")
    if isinstance(collection_flow, dict) and collection_flow.get("state"):
        return str(collection_flow["state"]), Phase.COLLECTION.value
    direction_flow = session_data.get("direction_flow")
    if isinstance(direction_flow, dict) and direction_flow.get("state"):
        return str(direction_flow["state"]), Phase.DIRECTION.value
    return DirectionState.INITIAL.value, Phase.DIRECTION.value


def _build_dev_snapshot(session_id: str) -> DialogueDevSnapshot:
    paths = _session_artifact_paths(session_id)
    session_data = _read_json_file(paths["session"])
    stage, phase = _stage_phase_from_session_data(session_data)
    processed_path = paths["data"] / "processed.json"
    collected_path = paths["data"] / "collected.json"
    analysis_flow = (session_data or {}).get("analysis_flow")
    has_analysis_flow_result = isinstance(analysis_flow, dict) and bool(
        analysis_flow.get("analysis_result")
    )
    artifacts = {
        "session": paths["session"].exists(),
        "analysis": paths["analysis"].exists() or has_analysis_flow_result,
        "collection": collected_path.exists(),
        "processing": processed_path.exists(),
        "collection_status": paths["collection_status"].exists(),
        "research_log": paths["research_log"].exists(),
        "reasoning_log": paths["reasoning_log"].exists(),
    }
    updated_at = _latest_mtime(
        [
            paths["session"],
            paths["analysis"],
            collected_path,
            processed_path,
            paths["collection_status"],
            paths["research_log"],
            paths["reasoning_log"],
        ]
    )
    return DialogueDevSnapshot(
        session_id=session_id,
        title=_snapshot_title(session_id, session_data),
        stage=stage,
        phase=phase,
        updated_at=updated_at,
        artifacts=artifacts,
    )


async def _build_dev_snapshot_db(
    session_id: str, uow: UnitOfWork
) -> DialogueDevSnapshot:
    """Build a dev snapshot by checking both DB tables and filesystem for artifacts."""
    paths = _session_artifact_paths(session_id)

    # Check DB for data
    has_collection = bool(await uow.collection_attempts.get_latest(session_id))
    has_processing = bool(await uow.processing_attempts.get_latest(session_id))
    analysis_row = await uow.analysis_sessions.get_by_session(session_id)
    has_analysis = bool(analysis_row and (analysis_row.analysis_draft or analysis_row.processing_result))

    # Determine stage/phase from DB session row
    session_row = await uow.sessions.get(session_id)
    stage, phase = DirectionState.INITIAL.value, Phase.DIRECTION.value
    title = session_id
    if session_row:
        if session_row.analysis_state:
            stage, phase = session_row.analysis_state, Phase.ANALYSIS.value
        elif session_row.processing_state:
            stage, phase = session_row.processing_state, Phase.PROCESSING.value
        elif session_row.collection_state:
            stage, phase = session_row.collection_state, Phase.COLLECTION.value
        elif session_row.direction_state:
            stage, phase = session_row.direction_state, Phase.DIRECTION.value
        if session_row.direction_context:
            try:
                ctx = json.loads(session_row.direction_context)
                initial_query = ctx.get("initial_query", "")
                if initial_query:
                    title = str(initial_query)[:90]
            except (json.JSONDecodeError, AttributeError):
                pass

    # Merge with filesystem artifacts for legacy sessions
    processed_path = paths["data"] / "processed.json"
    collected_path = paths["data"] / "collected.json"
    artifacts = {
        "session": paths["session"].exists() or session_row is not None,
        "analysis": paths["analysis"].exists() or has_analysis,
        "collection": collected_path.exists() or has_collection,
        "processing": processed_path.exists() or has_processing,
        "collection_status": paths["collection_status"].exists(),
        "research_log": paths["research_log"].exists(),
        "reasoning_log": paths["reasoning_log"].exists(),
    }

    # Pick the most recent timestamp across DB and filesystem
    updated_at = _latest_mtime([
        paths["session"], paths["analysis"], collected_path,
        processed_path, paths["collection_status"],
        paths["research_log"], paths["reasoning_log"],
    ])
    if session_row and session_row.updated_at:
        db_ts = session_row.updated_at.isoformat()
        if not updated_at or db_ts > updated_at:
            updated_at = db_ts

    return DialogueDevSnapshot(
        session_id=session_id,
        title=title,
        stage=stage,
        phase=phase,
        updated_at=updated_at,
        artifacts=artifacts,
    )


def _replace_session_id_in_text(path: Path, source_id: str, target_id: str) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace(source_id, target_id), encoding="utf-8")


def _copy_text_artifact(
    source_path: Path, target_path: Path, source_id: str, target_id: str
) -> None:
    if not source_path.exists():
        return
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
    _replace_session_id_in_text(target_path, source_id, target_id)


def _copy_directory_artifact(
    source_path: Path, target_path: Path, source_id: str, target_id: str
) -> None:
    if not source_path.exists():
        return
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        shutil.rmtree(target_path)
    shutil.copytree(source_path, target_path)
    for child in target_path.rglob("*"):
        if child.is_file() and child.suffix.lower() in {
            ".json",
            ".jsonl",
            ".md",
            ".txt",
        }:
            _replace_session_id_in_text(child, source_id, target_id)


async def _clone_dev_artifacts(
    source_id: str, target_id: str, uow: UnitOfWork
) -> None:
    """Clone all session data from source to target for dev/testing purposes.

    Copies DB rows (collection, processing, analysis) first, then any legacy
    filesystem artifacts for backwards compatibility with old sessions.
    """
    source_exists_in_db = await uow.sessions.exists(source_id)
    source_paths = _session_artifact_paths(source_id)

    if not source_exists_in_db and not source_paths["session"].exists():
        raise HTTPException(status_code=404, detail="Source session not found")

    # --- DB copy (primary path for all current sessions) ---
    if source_exists_in_db:
        # Ensure target session row exists before inserting child rows
        target_row = await uow.sessions.get(source_id)
        if target_row:
            from src.db.models.session_tables import SessionTable
            new_row = SessionTable(**{
                k: v for k, v in target_row.model_dump().items() if k != "id"
            })
            new_row.id = target_id
            await uow.sessions.upsert(new_row)

        # Copy collection attempts
        collection_attempts = await uow.collection_attempts.get_all(source_id)
        for attempt in collection_attempts:
            await uow.collection_attempts.append(
                target_id, attempt.pir, attempt.raw_response
            )

        # Copy processing attempts
        processing_attempts = await uow.processing_attempts.get_all(source_id)
        for attempt in processing_attempts:
            await uow.processing_attempts.append(
                target_id, attempt.pir, attempt.raw_result
            )

        # Copy analysis session
        analysis_row = await uow.analysis_sessions.get_by_session(source_id)
        if analysis_row:
            await uow.analysis_sessions.get_or_create(target_id)
            if analysis_row.processing_result:
                await uow.analysis_sessions.save_draft(
                    target_id,
                    analysis_row.processing_result,
                    analysis_row.analysis_draft or "",
                )
            if analysis_row.latest_council_note:
                await uow.analysis_sessions.save_council_note(
                    target_id, analysis_row.latest_council_note
                )

        await uow.commit()
        logger.info("[DevTools] Cloned DB data from %s to %s", source_id, target_id)

    # --- Legacy filesystem copy (fallback for old sessions) ---
    target_paths = _session_artifact_paths(target_id)
    _copy_text_artifact(
        source_paths["session"], target_paths["session"], source_id, target_id
    )
    _copy_text_artifact(
        source_paths["analysis"], target_paths["analysis"], source_id, target_id
    )
    _copy_text_artifact(
        source_paths["collection_status"],
        target_paths["collection_status"],
        source_id,
        target_id,
    )
    _copy_text_artifact(
        source_paths["research_log"], target_paths["research_log"], source_id, target_id
    )
    _copy_text_artifact(
        source_paths["reasoning_log"], target_paths["reasoning_log"], source_id, target_id
    )
    _copy_directory_artifact(
        source_paths["data"], target_paths["data"], source_id, target_id
    )


def _ensure_collection_flow(session: IntelligenceSession) -> CollectionFlow:
    if session.collection_flow is None:
        session.collection_flow = CollectionFlow(
            session_id=session.session_id,
            pir=session.direction_flow.current_pir or "",
            direction_context=session.direction_flow.context,
            research_logger=session.research_logger,
        )
    session.direction_flow.state = DirectionState.COMPLETE
    return session.collection_flow


def _ensure_processing_flow(session: IntelligenceSession) -> ProcessingFlow:
    collection_flow = _ensure_collection_flow(session)
    collection_flow.state = CollectionState.COMPLETE
    if session.processing_flow is None:
        session.processing_flow = ProcessingFlow(
            session_id=session.session_id,
            pir=session.direction_flow.current_pir or collection_flow.pir or "",
            direction_context=session.direction_flow.context,
            research_logger=session.research_logger,
        )
    return session.processing_flow


def _ensure_analysis_flow(session: IntelligenceSession) -> AnalysisFlow:
    processing_flow = _ensure_processing_flow(session)
    processing_flow.state = ProcessingState.COMPLETE
    if session.analysis_flow is None:
        session.analysis_flow = AnalysisFlow(
            session_id=session.session_id,
            pir=session.direction_flow.current_pir or processing_flow.pir or "",
            research_logger=session.research_logger,
        )
    return session.analysis_flow


async def _hydrate_analysis_flow_from_store(
    session: IntelligenceSession, uow: UnitOfWork | None = None
) -> None:
    analysis_flow = _ensure_analysis_flow(session)
    if analysis_flow.analysis_result:
        return
    try:
        state = await AnalysisSessionStore(uow=uow).load(session.session_id)
    except ValueError:
        return
    if not state or not state.processing_result or not state.analysis_draft:
        return
    analysis_flow.analysis_result = {
        "processing_result": state.processing_result.model_dump(mode="json"),
        "analysis_draft": state.analysis_draft.model_dump(mode="json"),
        "latest_council_note": (
            state.latest_council_note.model_dump(mode="json")
            if state.latest_council_note
            else None
        ),
        "collection_coverage": None,
        "data_source": "session",
    }


async def _apply_dev_restore_stage(
    session: IntelligenceSession,
    target_stage: str | None,
    target_phase: str | None,
    uow: UnitOfWork | None = None,
) -> None:
    if not target_stage:
        return
    phase = (
        target_phase
        or _stage_phase_from_session_data(
            _read_json_file(_session_artifact_paths(session.session_id)["session"])
        )[1]
    )

    if phase == Phase.DIRECTION.value:
        try:
            direction_state = DirectionState(target_stage)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail="Invalid direction stage"
            ) from exc
        session.collection_flow = None
        session.processing_flow = None
        session.analysis_flow = None
        session.council_flow = None
        session.direction_flow.force_state(
            direction_state,
            current_pir=session.direction_flow.current_pir,
            sub_state=_default_dev_sub_state(direction_state.value),
        )
        return

    if phase == Phase.COLLECTION.value:
        try:
            collection_state = CollectionState(target_stage)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail="Invalid collection stage"
            ) from exc
        collection_flow = _ensure_collection_flow(session)
        session.processing_flow = None
        session.analysis_flow = None
        session.council_flow = None
        collection_flow.state = collection_state
        return

    if phase == Phase.PROCESSING.value:
        processing_flow = _ensure_processing_flow(session)
        session.analysis_flow = None
        session.council_flow = None
        if target_stage == DirectionState.COMPLETE.value:
            processing_flow.state = ProcessingState.COMPLETE
            return
        try:
            processing_flow.state = ProcessingState(target_stage)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail="Invalid processing stage"
            ) from exc
        return

    if phase == Phase.ANALYSIS.value:
        analysis_flow = _ensure_analysis_flow(session)
        if target_stage == AnalysisState.COMPLETE.value:
            analysis_flow.state = AnalysisState.COMPLETE
            await _hydrate_analysis_flow_from_store(session, uow=uow)
            if session.council_flow is None:
                session.council_flow = CouncilFlow(
                    session_id=session.session_id,
                    research_logger=session.research_logger,
                )
            return
        try:
            analysis_flow.state = AnalysisState(target_stage)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail="Invalid analysis stage"
            ) from exc


def _try_parse_json(raw: str | None) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        try:
            return json.loads(raw, strict=False)
        except json.JSONDecodeError:
            pass
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.I)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                try:
                    return json.loads(match.group(1), strict=False)
                except json.JSONDecodeError:
                    return None
    return None


def _latest_attempt(path: Path) -> str | None:
    data = _read_json_file(path)
    attempts = data.get("attempts") if data else None
    if isinstance(attempts, list) and attempts:
        latest = attempts[-1]
        return latest if isinstance(latest, str) else json.dumps(latest)
    return None


async def _collection_display_payload(
    session_id: str, uow: UnitOfWork | None = None
) -> dict[str, Any] | None:
    # DB path (primary — all real sessions use DB)
    if uow:
        try:
            attempts = await uow.collection_attempts.get_all(session_id)
            if attempts:
                return CollectionService.parse_collected_data(attempts[-1].raw_response)
        except Exception:
            logger.exception("[DevTools] DB collection load failed for %s", session_id)

    # Legacy filesystem fallback for old sessions
    collected_path = _session_artifact_paths(session_id)["data"] / "collected.json"
    parsed = _try_parse_json(_latest_attempt(collected_path))
    if not isinstance(parsed, dict):
        return None
    collected_data = parsed.get("collected_data")
    if not isinstance(collected_data, list):
        return None

    summaries: dict[str, dict[str, Any]] = {}
    for item in collected_data:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or "unknown")
        summary = summaries.setdefault(
            source,
            {"display_name": source, "count": 0, "resource_ids": [], "has_content": False},
        )
        summary["count"] += 1
        resource_id = item.get("resource_id")
        if resource_id and resource_id not in summary["resource_ids"]:
            summary["resource_ids"].append(resource_id)
        if item.get("content"):
            summary["has_content"] = True

    return {"collected_data": collected_data, "source_summary": list(summaries.values())}


async def _processing_payload(
    session_id: str, uow: UnitOfWork | None = None
) -> dict[str, Any] | None:
    try:
        result = await ProcessingResultStore(uow=uow).get_processing_result(session_id)
    except Exception:
        return None
    return result.model_dump(mode="json")


async def _analysis_payload(
    session: IntelligenceSession, uow: UnitOfWork | None = None
) -> dict[str, Any] | None:
    if session.analysis_flow and session.analysis_flow.analysis_result:
        payload = dict(session.analysis_flow.analysis_result)
        payload.setdefault("latest_council_note", None)
        payload.setdefault("collection_coverage", None)
        payload.setdefault("data_source", "session")
        return payload

    try:
        state = await AnalysisSessionStore(uow=uow).load(session.session_id)
    except ValueError:
        return None
    if not state or not state.processing_result or not state.analysis_draft:
        return None
    return {
        "processing_result": state.processing_result.model_dump(mode="json"),
        "analysis_draft": state.analysis_draft.model_dump(mode="json"),
        "latest_council_note": (
            state.latest_council_note.model_dump(mode="json")
            if state.latest_council_note
            else None
        ),
        "collection_coverage": None,
        "data_source": "session",
    }


def _summary_payload(session: IntelligenceSession) -> dict[str, str]:
    context = session.direction_flow.context
    lines = [
        f"Scope: {context.scope or 'n/a'}",
        f"Timeframe: {context.timeframe or 'n/a'}",
        "Targets: "
        + (", ".join(context.target_entities) if context.target_entities else "n/a"),
        "Threat actors: "
        + (", ".join(context.threat_actors) if context.threat_actors else "n/a"),
        f"Priority focus: {context.priority_focus or 'n/a'}",
    ]
    return {"summary": "\n".join(lines)}


async def _build_dev_hydrated_messages(
    session: IntelligenceSession,
    target_stage: str,
    target_phase: str,
    uow: UnitOfWork | None = None,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    initial_query = session.direction_flow.context.initial_query
    if initial_query:
        messages.append({"text": initial_query, "sender": "user"})

    messages.append(
        {
            "text": json.dumps(_summary_payload(session)),
            "sender": "system",
            "type": "summary",
            "data": _summary_payload(session),
        }
    )

    include_pir = (
        target_phase
        in {
            Phase.DIRECTION.value,
            Phase.COLLECTION.value,
            Phase.PROCESSING.value,
            Phase.ANALYSIS.value,
        }
        and target_stage != DirectionState.SUMMARY_CONFIRMING.value
    )
    if include_pir and session.direction_flow.current_pir:
        pir_data = _try_parse_json(session.direction_flow.current_pir)
        messages.append(
            {
                "text": session.direction_flow.current_pir,
                "sender": "system",
                "type": "pir",
                "data": pir_data if isinstance(pir_data, dict) else None,
            }
        )

    if target_phase in {
        Phase.COLLECTION.value,
        Phase.PROCESSING.value,
        Phase.ANALYSIS.value,
    }:
        if session.collection_flow and session.collection_flow.collection_plan:
            messages.append(
                {
                    "text": session.collection_flow.collection_plan,
                    "sender": "system",
                    "type": "plan",
                    "data": {
                        "plan": session.collection_flow.collection_plan,
                        "suggested_sources": session.collection_flow.selected_sources,
                    },
                }
            )
        collection_data = await _collection_display_payload(session.session_id, uow=uow)
        if collection_data:
            messages.append(
                {
                    "text": "Collection complete",
                    "sender": "system",
                    "type": "collection",
                    "data": collection_data,
                }
            )

    if target_phase in {Phase.PROCESSING.value, Phase.ANALYSIS.value}:
        processing_data = await _processing_payload(session.session_id, uow=uow)
        if processing_data:
            messages.append(
                {
                    "text": "Processing complete - results are ready for review.",
                    "sender": "system",
                    "type": "processing",
                    "data": processing_data,
                }
            )

    if target_phase == Phase.ANALYSIS.value:
        analysis_data = await _analysis_payload(session, uow=uow)
        if analysis_data:
            messages.append(
                {
                    "text": "Analysis draft is ready.",
                    "sender": "system",
                    "type": "analysis",
                    "data": analysis_data,
                }
            )

    return messages


def _get_mcp_client() -> MCPClient:
    return MCPClient()


def _get_review_service() -> ReviewService:
    llm = LLMService(model=_GEMINI_MODEL)
    review_mcp_client = MCPClient(server_url=_REVIEW_MCP_URL)
    return ReviewService(llm, review_mcp_client)


def _build_orchestrator(session: IntelligenceSession) -> AIOrchestrator:
    """
    Builds AIorchestrator for the given session. Will use LLM model stated as global value

    Args:
        session: The active session

    Returns:
        An instance of AI orchestrator
    """
    return AIOrchestrator(
        research_logger=session.research_logger,
        generator_model=_GEMINI_MODEL,
        reviewer_model=_GEMINI_MODEL,
    )


async def _handle_processing_phase(
    session: IntelligenceSession,
    request: DialogueMessageRequest,
    mcp_client: MCPClient,
    orchestrator: AIOrchestrator,
    review_service: ReviewService,
    uow: UnitOfWork,
) -> DialogueMessageResponse:
    """
    handles messages during the processing phase of the investigation.

    The messages can be sent to different state if "gather_more" is true for additional information

    Args:
        session: current session
        request: message from the frontend
        mcp_client: client used to start processing serbice
        uow: Unit of Work for DB persistence

    Returns:
        response to the frontend
    """
    assert session.processing_flow is not None
    logger.info(
        f"[Session {request.session_id}] Message received — state={session.processing_flow.state}, approved={request.approved}"
    )
    # If user wants to gather more, we reset current state and shift to collection phase
    if request.gather_more:
        if not session.collection_flow:
            raise HTTPException(status_code=400, detail="No collection flow found")
        session.processing_flow = None
        session.collection_flow.state = CollectionState.REVIEWING
        await _save_session(session, uow)
        return _convert_to_message_response(
            DialogueResponse(
                action=DialogueAction.SELECT_GAPS, content=_GATHER_MORE_CONTENT
            ),
            stage=session.collection_flow.state.value,
            phase=Phase.COLLECTION,
            sub_state=_SUB_STATE_GATHER_MORE,
        )
    processing_service = ProcessingService(mcp_client)

    # Process user message in state machine
    response = await session.processing_flow.process_user_message(
        user_message=request.message,
        processing_service=processing_service,
        approved=request.approved,
        uow=uow,
    )
    # Transition: ProcessingFlow COMPLETE → start AnalysisFlow + CouncilFlow
    if (
        session.processing_flow.state == ProcessingState.COMPLETE
        and session.analysis_flow is None
    ):
        session.analysis_flow = AnalysisFlow(
            session_id=request.session_id,
            pir=session.processing_flow.pir,
            research_logger=session.research_logger,
        )
        analysis_service = AnalysisService(mcp_client)
        selected_perspectives = (
            [
                p.value.lower()
                for p in (session.direction_flow.context.perspectives or [])
            ]
            if session.direction_flow and session.direction_flow.context
            else None
        )
        init_response = await session.analysis_flow.initialize(
            processing_service=ProcessingResultStore(uow=uow),
            analysis_service=analysis_service,
            orchestrator=orchestrator,
            reviewer=review_service,
            selected_perspectives=selected_perspectives,
        )
        session.council_flow = CouncilFlow(
            session_id=request.session_id,
            research_logger=session.research_logger,
        )
        await _save_session(session, uow)
        return _convert_to_message_response(
            init_response,
            stage=session.analysis_flow.state.value,
            phase=Phase.ANALYSIS,
        )

    # Save current session and return message
    await _save_session(session, uow)
    return _convert_to_message_response(
        response, stage=session.processing_flow.state.value, phase=Phase.PROCESSING
    )


async def _handle_collection_phase(
    session: IntelligenceSession,
    request: DialogueMessageRequest,
    mcp_client: MCPClient,
    orchestrator: AIOrchestrator,
    review_service: ReviewService,
    uow: UnitOfWork,
) -> DialogueMessageResponse:
    """
    Handles incoming messages during the collection phase
    All messages will be used in collection flow. If the phase ends, we initizalize processing phase automatically.

    Args:
        session: The active session
        Requets: The incoming request from frontend
        mcp_client: client used to initialize collection
        orchestator: AI orchestrator used to controll dual AI instance
        review_service: Service for handling reviewing
        uow: Unit of Work for DB persistence
    """
    assert session.collection_flow is not None
    collection_service = CollectionService(mcp_client)
    logger.info(
        f"[Session {request.session_id}] Message received — state={session.collection_flow.state}, approved={request.approved}"
    )
    # Process user message in state machine
    response = await session.collection_flow.process_user_message(
        user_message=request.message,
        collection_service=collection_service,
        approved=request.approved,
        selected_sources=request.selected_sources,
        orchestrator=orchestrator,
        reviewer=review_service,
        gather_more=request.gather_more,
        uow=uow,
    )
    # Initialize processing state if finished with collection
    if (
        session.collection_flow.state == CollectionState.COMPLETE
        and session.processing_flow is None
    ):
        processing_service = ProcessingService(mcp_client)
        session.processing_flow = ProcessingFlow(
            session_id=request.session_id,
            pir=session.collection_flow.pir,
            direction_context=session.collection_flow.direction_context,
            research_logger=session.research_logger,
        )
        init_response = await session.processing_flow.initialize(
            processing_service=processing_service,
            orchestrator=orchestrator,
            reviewer=review_service,
            uow=uow,
        )
        await _save_session(session, uow)
        return _convert_to_message_response(
            init_response,
            stage=session.processing_flow.state.value,
            phase=Phase.PROCESSING,
        )

    await _save_session(session, uow)
    return _convert_to_message_response(
        response,
        stage=session.collection_flow.state.value,
        phase=Phase.COLLECTION,
    )


async def _handle_direction_phase(
    session: IntelligenceSession,
    request: DialogueMessageRequest,
    mcp_client: MCPClient,
    orchestrator: AIOrchestrator,
    review_service: ReviewService,
    uow: UnitOfWork,
) -> DialogueMessageResponse:
    """
    Handles incoming messages during the direction phase
    All messages will be used in direction flow.

    Args:
        session: The active session
        Requets: The incoming request from frontend
        mcp_client: client used to initialize collection
        orchestator: AI orchestrator used to controll dual AI instance
        review_service: Service for handling reviewing
        uow: Unit of Work for DB persistence
    """
    direction_flow = session.direction_flow
    logger.info(
        f"[Session {request.session_id}] Message received — state={direction_flow.state}, perspectives={request.perspectives}, approved={request.approved}"
    )
    service = DialogueService(mcp_client, None)

    # Process user message in state machine
    response = await direction_flow.process_user_message(
        request.message,
        service,
        request.perspectives,
        request.approved,
        orchestrator=orchestrator,
        reviewer=review_service,
        language=request.language,
        settings_timeframe=request.settings_timeframe,
    )

    # Transition: DirectionFlow COMPLETE → start CollectionFlow
    if (
        direction_flow.state == DirectionState.COMPLETE
        and session.collection_flow is None
        and direction_flow.current_pir
    ):
        collection_service = CollectionService(mcp_client)
        session.collection_flow = CollectionFlow(
            session_id=request.session_id,
            pir=direction_flow.current_pir,
            direction_context=direction_flow.context,
            research_logger=session.research_logger,
        )
        init_response = await session.collection_flow.initialize(
            collection_service, uow=uow
        )
        await _save_session(session, uow)
        return _convert_to_message_response(
            init_response,
            stage=session.collection_flow.state.value,
            phase=Phase.COLLECTION,
        )

    # Convert internal response to API format and return
    default_sub_state = (
        _SUB_STATE_AWAITING_DECISION
        if direction_flow.state
        in (DirectionState.SUMMARY_CONFIRMING, DirectionState.PIR_CONFIRMING)
        else None
    )
    await _save_session(session, uow)
    return _convert_to_message_response(
        response,
        stage=direction_flow.state.value,
        phase=Phase.DIRECTION,
        sub_state=direction_flow.sub_state or default_sub_state,
    )


async def _handle_analysis_phase(
    session: IntelligenceSession,
    _request: DialogueMessageRequest,
) -> DialogueMessageResponse:
    assert session.analysis_flow is not None
    response = await session.analysis_flow.process_user_message()
    return _convert_to_message_response(
        response,
        stage=session.analysis_flow.state.value,
        phase=Phase.ANALYSIS,
    )


async def _handle_council_phase(
    session: IntelligenceSession,
    request: DialogueMessageRequest,
    uow: UnitOfWork,
) -> DialogueMessageResponse:
    if session.council_flow is None:
        from src.models.dialogue import DialogueAction, DialogueResponse

        return _convert_to_message_response(
            DialogueResponse(
                action=DialogueAction.ERROR,
                content="Council is not available until analysis is complete.",
            ),
            stage="unavailable",
            phase=Phase.ANALYSIS,
        )
    perspectives = request.council_perspectives or request.perspectives
    response = await session.council_flow.process_user_message(
        debate_point=request.council_debate_point,
        finding_ids=request.council_finding_ids,
        selected_perspectives=perspectives,
        council_service=CouncilService(),
        analysis_flow=session.analysis_flow,
        council_settings=request.council_settings,
    )
    await _save_session(session, uow)
    return _convert_to_message_response(
        response,
        stage=session.council_flow.state.value,
        phase=Phase.COUNCIL,
    )


async def _dispatch_message(
    request: DialogueMessageRequest,
    mcp_client: MCPClient,
    review_service: ReviewService,
    uow: UnitOfWork,
) -> DialogueMessageResponse:
    session = await _get_or_create_session(request.session_id, uow)
    orchestrator = _build_orchestrator(session)
    if session.analysis_flow:
        if request.council_debate_point or request.council_finding_ids:
            return await _handle_council_phase(session, request, uow)
        return await _handle_analysis_phase(session, request)
    if session.processing_flow:
        return await _handle_processing_phase(
            session, request, mcp_client, orchestrator, review_service, uow
        )
    if session.collection_flow:
        return await _handle_collection_phase(
            session, request, mcp_client, orchestrator, review_service, uow
        )
    return await _handle_direction_phase(
        session, request, mcp_client, orchestrator, review_service, uow
    )


@router.post("/message")
async def send_message(
    request: DialogueMessageRequest,
    mcp_client: MCPClient = Depends(_get_mcp_client),
    review_service: ReviewService = Depends(_get_review_service),
    uow: UnitOfWork = Depends(get_uow),
) -> DialogueMessageResponse:
    """
    Process a user message and continue the flow in the dialogue state machine.

    If the session_id does not exist, a new session will be created


    Args:
        request DialogueMessageRequest:
            - usermessage : The message the user sent
            - session_id : The session id for the given session
            - Perspectives : What perspectives the user have chosen
            - Approved status: If the user approves or rejects ai output. Is only used when the user is given a choice.

    Returns:
        A response with the next question or summary and canonical action/state metadata.

    Raises:
        Any exception given by DirectionFlow or MCPClient
    """
    timeout_seconds = _dialogue_request_timeout_seconds(request)
    try:
        return await asyncio.wait_for(
            _dispatch_message(request, mcp_client, review_service, uow),
            timeout=timeout_seconds,
        )
    except TimeoutError:
        session = _sessions.get(request.session_id)
        if session is not None:
            stage, phase = _get_active_stage_and_phase(session)
        else:
            stage, phase = "timeout", Phase.DIRECTION
        logger.error(
            "[Session %s] Dialogue request timed out after %.1fs",
            request.session_id,
            timeout_seconds,
        )
        return DialogueMessageResponse(
            question=(
                "The request timed out while waiting for the AI or an MCP tool. "
                "Try again, or narrow the request if it was a large collection run."
            ),
            action=DialogueAction.ERROR,
            stage=stage,
            phase=phase.value,
            sub_state=None,
        )


@router.get("/collection-status/{session_id}")
async def get_collection_status(session_id: str):
    """Return the live collection tool-call status for a session.

    The frontend polls this every ~1.5 s while isCollecting is true to drive
    the per-source progress indicator in the IntelligencePanel.
    Returns 404 if no status file exists yet for the session.
    """
    status = CollectionStatusTracker.read(session_id)
    if status is None:
        raise HTTPException(status_code=404, detail="No collection status found")
    return status


@router.get("/dev/state")
async def get_dev_state(
    session_id: str, uow: UnitOfWork = Depends(get_uow)
) -> DialogueDevStateResponse:
    """DEV endpoint: read current dialogue state for a session."""
    _ensure_dev_tools_enabled()
    session = await _get_or_create_session(session_id, uow)
    return _build_dev_state_response(session_id, session)


@router.get("/dev/snapshots")
async def list_dev_snapshots(
    uow: UnitOfWork = Depends(get_uow),
) -> list[DialogueDevSnapshot]:
    """DEV endpoint: list saved sessions with reusable artifacts."""
    _ensure_dev_tools_enabled()

    session_ids: set[str] = set()

    # Primary: discover sessions from the DB
    try:
        db_rows = await uow.sessions.list_all()
        for row in db_rows:
            if _SESSION_ID_RE.fullmatch(row.id):
                session_ids.add(row.id)
    except Exception:
        logger.exception("[DevTools] Failed to list sessions from DB")

    # Legacy: also scan filesystem for old sessions not yet in DB
    ensure_sessions_dir()
    for path in _SESSIONS_DIR.glob("*.json"):
        if path.name.endswith(".analysis.json"):
            continue
        session_ids.add(path.stem)
    if _SESSION_DATA_DIR.exists():
        session_ids.update(
            path.name for path in _SESSION_DATA_DIR.iterdir() if path.is_dir()
        )
    if _OUTPUTS_DIR.exists():
        for path in _OUTPUTS_DIR.glob("research_log_*.jsonl"):
            session_ids.add(path.name.removeprefix("research_log_").removesuffix(".jsonl"))
        for path in _OUTPUTS_DIR.glob("reasoning_log_*.json"):
            session_ids.add(path.name.removeprefix("reasoning_log_").removesuffix(".json"))

    # Build snapshot for each session — check both DB and filesystem for artifacts
    snapshots = []
    for session_id in session_ids:
        if not _SESSION_ID_RE.fullmatch(session_id):
            continue
        snapshot = await _build_dev_snapshot_db(session_id, uow)
        snapshots.append(snapshot)

    snapshots = [
        s for s in snapshots
        if any(
            s.artifacts.get(key, False)
            for key in ("analysis", "collection", "processing", "research_log", "reasoning_log")
        )
    ]
    return sorted(snapshots, key=lambda item: item.updated_at or "", reverse=True)


@router.post("/dev/restore")
async def restore_dev_snapshot(
    request: DialogueDevRestoreRequest,
    uow: UnitOfWork = Depends(get_uow),
) -> DialogueDevRestoreResponse:
    """DEV endpoint: clone prior session data/logs into the active session."""
    _ensure_dev_tools_enabled()
    source_id = _validate_dev_session_id(request.source_session_id)
    target_id = _validate_dev_session_id(request.target_session_id)

    if source_id != target_id:
        await _clone_dev_artifacts(source_id, target_id, uow)
    _sessions.pop(target_id, None)
    session = await _get_or_create_session(target_id, uow)
    await _apply_dev_restore_stage(session, request.target_stage, request.target_phase, uow=uow)
    await _save_session(session, uow)

    state = _build_dev_state_response(target_id, session)
    messages = await _build_dev_hydrated_messages(session, state.stage, state.phase, uow=uow)
    return DialogueDevRestoreResponse(
        **state.model_dump(),
        source_session_id=source_id,
        messages=messages,
    )


@router.post("/dev/state")
async def set_dev_state(
    request: DialogueDevStateRequest, uow: UnitOfWork = Depends(get_uow)
) -> DialogueDevStateResponse:
    """DEV endpoint: force a session into a specific dialogue stage."""
    _ensure_dev_tools_enabled()
    session = await _get_or_create_session(request.session_id, uow)
    try:
        stage = DirectionState(request.stage)
    except ValueError as exc:
        allowed = ", ".join(state.value for state in DirectionState)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage '{request.stage}'. Allowed: {allowed}",
        ) from exc

    session.direction_flow.force_state(
        stage,
        seed_context=request.seed_context,
        current_pir=request.current_pir,
        sub_state=request.sub_state,
    )
    return _build_dev_state_response(request.session_id, session)


@router.post("/dev/reset")
async def reset_dev_session(
    session_id: str, uow: UnitOfWork = Depends(get_uow)
) -> DialogueDevStateResponse:
    """DEV endpoint: reset a session to INITIAL."""
    _ensure_dev_tools_enabled()
    session = await _get_or_create_session(session_id, uow)
    session.direction_flow.force_state(DirectionState.INITIAL, sub_state=None)
    return _build_dev_state_response(session_id, session)
