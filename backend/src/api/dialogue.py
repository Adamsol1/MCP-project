from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/dialogue")


# Request model
class DialogueMessageRequest(BaseModel):
    message: str
    session_id: str


# Response Model
class DialogueMessageResponse(BaseModel):
    question: str
    type: str
    is_final: bool


@router.post("/message")
async def send_message(request: DialogueMessageRequest) -> DialogueMessageResponse:
    #
    # something

    return DialogueMessageResponse(
        question="What is the scope of your investigation", type="scope", is_final=False
    )
