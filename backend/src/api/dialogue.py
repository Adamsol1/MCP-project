import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from knowledge_bank.knowledge_registry import KNOWLEDGE_REGISTRY
from knowledge_bank.service import KnowledgeService
from src.mcp_client.client import MCPClient
from src.models.dialogue import DialogueAction, DialogueResponse
from src.services.ai_orchestrator import AIOrchestrator
from src.services.dialogue_flow import DialogueFlow, DialogueState
from src.services.dialogue_service import DialogueService
from src.services.reasearch_logger import ResearchLogger
from src.services.review_service import ReviewService

"""
API router for the dialogue flow.

Handles incoming messages from the frontend, routes them through
the dialogue state machine (DialogueFlow), and returns structured responses.

Sessions are stored in memory in `_sessions`
"""

router = APIRouter(prefix="/api/dialogue")
logger = logging.getLogger("app")
_server_path = str(
    Path(__file__).parent.parent.parent.parent / "mcp_server" / "src" / "server.py"
)

_knowledge_service = KnowledgeService(KNOWLEDGE_REGISTRY)
_knowledge_base_path = Path(__file__).parent.parent.parent  # → backend/

_sessions: dict[str, DialogueFlow] = {}
DEV_TOOLS_ENABLED = os.getenv("APP_ENV", "development") != "production"

_SESSIONS_DIR = Path(__file__).parent.parent.parent / "sessions"
_SESSIONS_DIR.mkdir(exist_ok=True)


def _save_session(flow: DialogueFlow) -> None:
    """Persist session state to disk so it survives server restarts."""
    path = _SESSIONS_DIR / f"{flow.session_id}.json"
    path.write_text(json.dumps(flow.to_dict()), encoding="utf-8")


def _load_session(session_id: str, research_logger) -> DialogueFlow | None:
    """Load a previously persisted session from disk. Returns None if not found."""
    path = _SESSIONS_DIR / f"{session_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    logger.info(f"[Session {session_id}] Restored from disk — state={data['state']}")
    return DialogueFlow.from_dict(data, research_logger=research_logger)


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


# Response Model
class DialogueMessageResponse(BaseModel):
    """
    Outgoing repsonse for the /message endpoint
    """

    question: str
    action: DialogueAction
    stage: str
    sub_state: str | None = None


class DialogueDevStateResponse(BaseModel):
    session_id: str
    stage: str
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


def _normalize_dialogue_action(action: DialogueAction | str) -> DialogueAction:
    if isinstance(action, DialogueAction):
        return action
    try:
        return DialogueAction(action)
    except ValueError as exc:
        raise ValueError(f"Unsupported dialogue action: {action}") from exc


def _convert_to_message_response(
    response: DialogueResponse,
    stage: str,
    sub_state: str | None = None,
) -> DialogueMessageResponse:
    """
    Converts internal DialogueRespone to the API respone format
    Example:
        Input:  DialogueResponse(action="ask_question", content="What is the scope?")
        Output: DialogueMessageResponse(question="What is the scope?", action="ask_question")

    """
    try:
        action = _normalize_dialogue_action(response.action)
    except ValueError as exc:
        logger.error("Failed to convert dialogue response action: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    result = DialogueMessageResponse(
        question=response.content,
        action=action,
        stage=stage,
        sub_state=sub_state,
    )
    return result


def _ensure_dev_tools_enabled():
    if not DEV_TOOLS_ENABLED:
        raise HTTPException(status_code=404, detail="Not found")


def _get_or_create_session(session_id: str) -> DialogueFlow:
    if session_id not in _sessions:
        research_logger = ResearchLogger(session_id=session_id)
        _sessions[session_id] = DialogueFlow(
            session_id=session_id, research_logger=research_logger
        )
    return _sessions[session_id]


def _build_dev_state_response(session_id: str, flow: DialogueFlow) -> DialogueDevStateResponse:
    state = flow.get_debug_state()
    return DialogueDevStateResponse(
        session_id=session_id,
        stage=state["stage"],
        sub_state=state["sub_state"],
        question_count=state["question_count"],
        max_questions=state["max_questions"],
        missing_context_fields=state["missing_context_fields"],
        has_sufficient_context=state["has_sufficient_context"],
        awaiting_user_decision=state["awaiting_user_decision"],
        has_modifications=state["has_modifications"],
    )


@router.post("/message")
async def send_message(request: DialogueMessageRequest) -> DialogueMessageResponse:
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
        Any exception given by DialogueFlow or MCPClient
    """
    # Checks if session_id is in memory. If not, try to restore from disk, else create new.
    if request.session_id not in _sessions:
        research_logger = ResearchLogger(session_id=request.session_id)
        _sessions[request.session_id] = _load_session(
            request.session_id, research_logger
        ) or DialogueFlow(
            session_id=request.session_id, research_logger=research_logger
        )

    flow = _sessions[request.session_id]
    logger.info(
        f"[Session {request.session_id}] Message received — state={flow.state}, perspectives={request.perspectives}, approved={request.approved}"
    )

    # TODO (PERFORMANCE): MCPClient spawns a new subprocess on every request — this is expensive.
    # Fix: add open()/close() to MCPClient using AsyncExitStack, store the client in _sessions
    # alongside DialogueFlow, and call client.close() + del _sessions[id] when the flow reaches COMPLETE.
    # See code review notes for full plan.
    client = MCPClient(_server_path)

    # Connect to mcp, and wait for response from state machine
    async with client.connect():
        service = DialogueService(
            client,
            None,
            knowledge_service=_knowledge_service,
            knowledge_base_path=str(_knowledge_base_path),
        )
        review_service = ReviewService(client)
        orchestrator = AIOrchestrator(
            research_logger=flow.research_logger,
            generator_model="gemini-2.0-flash",
            reviewer_model="gemini-2.0-flash",
        )
        response = await flow.process_user_message(
            request.message,
            service,
            request.perspectives,
            request.approved,
            orchestrator=orchestrator,
            reviewer=review_service,
            language=request.language,
            settings_timeframe=request.settings_timeframe,
        )

    # Convert internal response to API format and return
    default_sub_state = (
        "awaiting_decision"
        if flow.state in (DialogueState.SUMMARY_CONFIRMING, DialogueState.PIR_CONFIRMING)
        else None
    )
    converted_response = _convert_to_message_response(
        response,
        stage=flow.state.value,
        sub_state=flow.sub_state or default_sub_state,
    )

    # Persist updated session state to disk after every message
    _save_session(flow)

    return converted_response


@router.get("/dev/state")
async def get_dev_state(session_id: str) -> DialogueDevStateResponse:
    """DEV endpoint: read current dialogue state for a session."""
    _ensure_dev_tools_enabled()
    flow = _get_or_create_session(session_id)
    return _build_dev_state_response(session_id, flow)


@router.post("/dev/state")
async def set_dev_state(request: DialogueDevStateRequest) -> DialogueDevStateResponse:
    """DEV endpoint: force a session into a specific dialogue stage."""
    _ensure_dev_tools_enabled()
    flow = _get_or_create_session(request.session_id)
    try:
        stage = DialogueState(request.stage)
    except ValueError as exc:
        allowed = ", ".join(state.value for state in DialogueState)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage '{request.stage}'. Allowed: {allowed}",
        ) from exc

    flow.force_state(
        stage,
        seed_context=request.seed_context,
        current_pir=request.current_pir,
        sub_state=request.sub_state,
    )
    return _build_dev_state_response(request.session_id, flow)


@router.post("/dev/reset")
async def reset_dev_session(session_id: str) -> DialogueDevStateResponse:
    """DEV endpoint: reset a session to INITIAL."""
    _ensure_dev_tools_enabled()
    flow = _get_or_create_session(session_id)
    flow.force_state(DialogueState.INITIAL, sub_state=None)
    return _build_dev_state_response(session_id, flow)
