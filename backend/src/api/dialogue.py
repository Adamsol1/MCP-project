"""
API router for the dialogue flow.

Handles incoming messages from the frontend, routes them through
the dialogue state machine (DirectionFlow), and returns structured responses.

Sessions are cached in memory in `_sessions` and persisted to sessions.db.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.db.mappers import row_to_session, session_to_row
from src.db.unit_of_work import UnitOfWork, get_uow
from src.mcp_client.client import MCPClient
from src.models.dialogue import DialogueAction, DialogueResponse, Phase
from src.services.ai_orchestrator import AIOrchestrator
from src.services.collection_service import CollectionService
from src.services.collection_status import CollectionStatusTracker
from src.services.dialogue_service import DialogueService
from src.services.llm_service import LLMService
from src.services.processing_service import ProcessingService
from src.services.reasearch_logger import ResearchLogger
from src.services.review_service import ReviewService
from src.services.state_machines.collection_flow import CollectionFlow, CollectionState
from src.services.state_machines.direction_flow import DirectionFlow, DirectionState
from src.services.state_machines.processing_flow import ProcessingFlow

#Global values used in the file
_REVIEW_MCP_URL = os.getenv("REVIEW_MCP_URL", "http://127.0.0.1:8002/sse")
DEV_TOOLS_ENABLED = os.getenv("DEV_TOOLS_ENABLED", "true").lower() == "true"

_GEMINI_MODEL = "gemini-2.5-flash"
_GATHER_MORE_CONTENT = "What gaps would you like to fill? Describe what additional information to gather."
_SUB_STATE_GATHER_MORE = "awaiting_gather_more"
_SUB_STATE_AWAITING_DECISION = "awaiting_decision"

router = APIRouter(prefix="/api/dialogue")
logger = logging.getLogger("app")


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


async def _load_session(session_id: str, research_logger, uow: UnitOfWork) -> IntelligenceSession | None:
    """Load a previously persisted session from sessions.db.

    Returns None if not found.
    """
    row = await uow.sessions.get(session_id)
    if row is None:
        return None

    session = row_to_session(row, research_logger)
    logger.info(f"[Session {session_id}] Restored from DB")
    return session


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
        raise HTTPException(status_code=500, detail="Internal error: invalid dialogue action") from exc

    result = DialogueMessageResponse(
        question=response.content,
        action=action,
        stage=stage,
        phase=phase.value,
        sub_state=sub_state,
    )
    return result

#Temp
def _ensure_dev_tools_enabled():
    if not DEV_TOOLS_ENABLED:
        raise HTTPException(status_code=404, detail="Not found")


async def _get_or_create_session(session_id: str, uow: UnitOfWork) -> IntelligenceSession:
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
    return DialogueDevStateResponse(
        session_id=session_id,
        stage=active_stage,
        phase=active_phase.value,
        sub_state=state["sub_state"],
        question_count=state["question_count"],
        max_questions=state["max_questions"],
        missing_context_fields=state["missing_context_fields"],
        has_sufficient_context=state["has_sufficient_context"],
        awaiting_user_decision=state["awaiting_user_decision"],
        has_modifications=state["has_modifications"],
    )


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
    #If user wants to gather more, we reset current state and shift to collection phase
    if request.gather_more:
        if not session.collection_flow:
            raise HTTPException(status_code=400, detail="No collection flow found")
        session.processing_flow = None
        session.collection_flow.state = CollectionState.REVIEWING
        await _save_session(session, uow)
        return _convert_to_message_response(
            DialogueResponse(action=DialogueAction.SELECT_GAPS, content=_GATHER_MORE_CONTENT),
            stage=session.collection_flow.state.value,
            phase=Phase.COLLECTION,
            sub_state=_SUB_STATE_GATHER_MORE,
        )
    processing_service = ProcessingService(mcp_client)

    #Process user message in state machine
    response = await session.processing_flow.process_user_message(
        user_message=request.message,
        processing_service=processing_service,
        approved=request.approved,
        uow=uow,
    )
    #Save current session and return message
    await _save_session(session, uow)
    return _convert_to_message_response(response, stage=session.processing_flow.state.value, phase=Phase.PROCESSING)


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
    #Process user message in state machine
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
    #Initialize processing state if finished with collection
    if session.collection_flow.state == CollectionState.COMPLETE and session.processing_flow is None:
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

    #Process user message in state machine
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
        init_response = await session.collection_flow.initialize(collection_service, uow=uow)
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
    session = await _get_or_create_session(request.session_id, uow)
    orchestrator = _build_orchestrator(session)
    #Current state is processing
    if session.processing_flow:
        return await _handle_processing_phase(session, request, mcp_client, uow)
    #Current state is collection
    if session.collection_flow:
        return await _handle_collection_phase(session, request, mcp_client, orchestrator, review_service, uow)
    return await _handle_direction_phase(session, request, mcp_client, orchestrator, review_service, uow)


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
async def get_dev_state(session_id: str, uow: UnitOfWork = Depends(get_uow)) -> DialogueDevStateResponse:
    """DEV endpoint: read current dialogue state for a session."""
    _ensure_dev_tools_enabled()
    session = await _get_or_create_session(session_id, uow)
    return _build_dev_state_response(session_id, session)


@router.post("/dev/state")
async def set_dev_state(request: DialogueDevStateRequest, uow: UnitOfWork = Depends(get_uow)) -> DialogueDevStateResponse:
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
async def reset_dev_session(session_id: str, uow: UnitOfWork = Depends(get_uow)) -> DialogueDevStateResponse:
    """DEV endpoint: reset a session to INITIAL."""
    _ensure_dev_tools_enabled()
    session = await _get_or_create_session(session_id, uow)
    session.direction_flow.force_state(DirectionState.INITIAL, sub_state=None)
    return _build_dev_state_response(session_id, session)
