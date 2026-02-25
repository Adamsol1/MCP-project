import logging
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from src.mcp_client.client import MCPClient
from src.models.dialogue import DialogueResponse
from src.services.ai_orchestrator import AIOrchestrator
from src.services.dialogue_flow import DialogueFlow
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


_sessions: dict[str, DialogueFlow] = {}


# Request model
class DialogueMessageRequest(BaseModel):
    """
    Incoming request body for the /message endpoint
    """

    message: str
    session_id: str
    perspectives: list[str] = ["NEUTRAL"]
    approved: bool | None = None


# Response Model
class DialogueMessageResponse(BaseModel):
    """
    Outgoing repsonse for the /message endpoint
    """

    question: str
    type: str
    is_final: bool


"""
Action map that maps dialogueFlow action names to respone type, is_final).
Is final = True, indicates to the frontend that the conversaton is complete
"""
action_map = {
    "ask_question": ("question", False),
    "show_summary": ("summary", True),
    "show_pir": ("pir", True),
    "max_questions": ("summary", True),
    "complete": ("complete", True),
}


def _convert_to_message_response(response: DialogueResponse) -> DialogueMessageResponse:
    """
    Converts internal DialogueRespone to the API respone format
    Example:
        Input:  DialogueResponse(action="ask_question", content="What is the scope?")
        Output: DialogueMessageResponse(question="What is the scope?", type="question", is_final=False)

    """
    type_, is_final = action_map[response.action]
    result = DialogueMessageResponse(
        question=response.content,
        type=type_,
        is_final=is_final,
    )
    return result


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
        A response with the next question or summary, what type of respone, and if the dialogue flow is complete

    Raises:
        Any exception given by DialogueFlow or MCPClient
    """
    # Checks if session_id is in session. If not create a new session
    if request.session_id not in _sessions:
        research_logger = ResearchLogger(session_id=request.session_id)
        _sessions[request.session_id] = DialogueFlow(
            session_id=request.session_id, research_logger=research_logger
        )

    # Start a new dialogueFlow
    flow = _sessions[request.session_id]
    logger.info(
        f"[Session {request.session_id}] Message received — state={flow.state}, perspectives={request.perspectives}, approved={request.approved}"
    )

    # TODO (PERFORMANCE): MCPClient spawns a new subprocess on every request — this is expensive.
    # Fix: add open()/close() to MCPClient using AsyncExitStack, store the client in _sessions
    # alongside DialogueFlow, and call client.close() + del _sessions[id] when is_final=True.
    # See code review notes for full plan.
    client = MCPClient(_server_path)

    # Connect to mcp, and wait for response from state machine
    async with client.connect():
        service = DialogueService(client, None)
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
        )

    # Convert internal response to API format and return
    converted_response = _convert_to_message_response(response)

    return converted_response
