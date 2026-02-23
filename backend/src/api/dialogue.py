from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from src.services.reasearch_logger import ResearchLogger
from src.mcp_client.client import MCPClient
from src.models.dialogue import DialogueResponse
from src.services.ai_orchestrator import AIOrchestrator
from src.services.dialogue_flow import DialogueFlow
from src.services.dialogue_service import DialogueService
from src.services.review_service import ReviewService

router = APIRouter(prefix="/api/dialogue")
_server_path = str(
    Path(__file__).parent.parent.parent.parent / "mcp_server" / "src" / "server.py"
)
_sessions: dict[str, DialogueFlow] = {}


# Request model
class DialogueMessageRequest(BaseModel):
    message: str
    session_id: str
    perspectives: list[str] = ["NEUTRAL"]
    approved: bool | None = None


# Response Model
class DialogueMessageResponse(BaseModel):
    question: str
    type: str
    is_final: bool


# Map action → type og is_final
action_map = {
    "ask_question": ("question", False),
    "show_summary": ("summary", True),
    "show_pir": ("pir", True),
    "max_questions": ("summary", True),
    "complete": ("complete", True),
}


def _convert_to_message_response(response: DialogueResponse) -> DialogueMessageResponse:
    type_, is_final = action_map[response.action]
    result = DialogueMessageResponse(
        question=response.content,
        type=type_,
        is_final=is_final,
    )
    return result


@router.post("/message")
async def send_message(request: DialogueMessageRequest) -> DialogueMessageResponse:
    print(f"Perspectives received: {request.perspectives}")
    print(f"Approved: {request.approved}")

    if request.session_id not in _sessions:
        logger = ResearchLogger(session_id=request.session_id)
        _sessions[request.session_id] = DialogueFlow(session_id=request.session_id, logger=logger)

    flow = _sessions[request.session_id]

    # TODO (PERFORMANCE): MCPClient spawns a new subprocess on every request — this is expensive.
    # Fix: add open()/close() to MCPClient using AsyncExitStack, store the client in _sessions
    # alongside DialogueFlow, and call client.close() + del _sessions[id] when is_final=True.
    # See code review notes for full plan.
    client = MCPClient(_server_path)

    async with client.connect():
        service = DialogueService(client, None)
        review_service = ReviewService(client)
        orchestrator = AIOrchestrator(logger=ResearchLogger())
        response = await flow.process_user_message(
            request.message,
            service,
            request.perspectives,
            request.approved,
            orchestrator=orchestrator,
            reviewer=review_service,
        )

    converted_response = _convert_to_message_response(response)

    return converted_response

    # TODO: Frontend needs to handle "complete" state — currently no UI for finished flow
