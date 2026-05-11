"""Developer-only endpoints for direct LLM testing."""

from __future__ import annotations

import logging
import os
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services.ai.llm_config import get_llm_provider, request_llm_provider
from src.services.ai.providers import get_provider

logger = logging.getLogger("app")

router = APIRouter(prefix="/api/dev")

DEV_TOOLS_ENABLED = os.getenv("DEV_TOOLS_ENABLED", "true").lower() == "true"


class DevChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class DevChatRequest(BaseModel):
    messages: list[DevChatMessage] = Field(min_length=1)
    ai_provider: str | None = None
    model: str | None = None


class DevChatResponse(BaseModel):
    message: str
    provider: str
    model: str


@router.post("/llm-chat", response_model=DevChatResponse)
async def dev_llm_chat(request: DevChatRequest) -> DevChatResponse:
    """Send raw chat messages to the active LLM provider."""

    if not DEV_TOOLS_ENABLED:
        raise HTTPException(status_code=404, detail="Dev tools are disabled")

    try:
        with request_llm_provider(request.ai_provider):
            provider = get_provider(model=request.model)
            text = await provider.chat(
                [item.model_dump() for item in request.messages]
            )
            return DevChatResponse(
                message=text,
                provider=get_llm_provider(),
                model=provider.model,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("[dev_llm_chat] LLM request failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
