from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/dialogue")


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


@router.post("/message")
async def send_message(request: DialogueMessageRequest) -> DialogueMessageResponse:
    print(f"Perspectives received: {request.perspectives}")
    print(f"Approved: {request.approved}")

    # TODO: Translate DialogueFlow response.action to frontend format:
    # is_final = response.action in ("show_summary", "show_pir", "max_questions")
    # TODO: Frontend needs to handle "complete" state — currently no UI for finished flow



    # Hardcoded responses for testing the approve/reject flow
    if request.approved:
        return DialogueMessageResponse(
            question="Approved! Proceeding to intelligence gathering phase.", type="complete", is_final=False
        )

    return DialogueMessageResponse(
        question="What is the scope of your investigation", type="scope", is_final=False
    )

