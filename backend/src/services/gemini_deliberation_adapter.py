"""Direct Gemini API adapter for council deliberation."""

import asyncio
import logging
import os
from typing import Optional

from google import genai

logger = logging.getLogger(__name__)


class GeminiDeliberationAdapter:
    """Adapter compatible with the council engine's invoke contract."""

    MAX_PROMPT_CHARS = 100000

    def __init__(self, timeout: int = 60):
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)
        self.timeout = timeout

    async def invoke(
        self,
        prompt: str,
        model: str,
        context: Optional[str] = None,
        is_deliberation: bool = True,
        working_directory: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
    ) -> str:
        del is_deliberation
        del working_directory
        del reasoning_effort

        full_prompt = prompt
        if context:
            full_prompt = f"{context}\n\n{prompt}"

        if len(full_prompt) > self.MAX_PROMPT_CHARS:
            raise ValueError(
                f"Prompt too long ({len(full_prompt)} chars). "
                f"Maximum allowed: {self.MAX_PROMPT_CHARS} chars."
            )

        logger.info(
            "Executing Gemini API adapter: model=%s prompt_length=%s chars",
            model,
            len(full_prompt),
        )

        response = await asyncio.wait_for(
            self.client.aio.models.generate_content(
                model=model,
                contents=full_prompt,
            ),
            timeout=self.timeout,
        )

        if not response.text:
            raise ValueError(f"Gemini model {model} returned empty response")
        return response.text.strip()
