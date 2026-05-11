"""Helpers for creating Google Gemini clients safely."""

from __future__ import annotations

import logging
import os
from typing import Any

from google import genai
from google.genai._api_client import BaseApiClient

logger = logging.getLogger("app")

_PATCHED = False


async def _safe_aclose(self: Any) -> None:
    try:
        async_httpx_client = getattr(self, "_async_httpx_client", None)
        http_options = getattr(self, "_http_options", None)
        custom_async_client = (
            getattr(http_options, "httpx_async_client", None)
            if http_options is not None
            else None
        )
        if async_httpx_client is not None and not custom_async_client:
            await async_httpx_client.aclose()

        aiohttp_session = getattr(self, "_aiohttp_session", None)
        custom_aiohttp_client = (
            getattr(http_options, "aiohttp_client", None)
            if http_options is not None
            else None
        )
        if aiohttp_session is not None and not custom_aiohttp_client:
            await aiohttp_session.close()
    except Exception as exc:
        logger.debug("[GeminiClient] Ignored SDK cleanup error: %s", exc)


def patch_gemini_cleanup() -> None:
    """Patch a google-genai cleanup bug for every client instance.

    google-genai 1.64.0 may schedule BaseApiClient.aclose() from __del__ even
    when the internal async httpx client was never initialized. That produces a
    noisy "Task exception was never retrieved" AttributeError. Patching the
    class method is intentional: clients can also be created by tests, reloads,
    or future code paths that do not go through create_gemini_client().
    """

    global _PATCHED
    if _PATCHED:
        return
    BaseApiClient.aclose = _safe_aclose
    _PATCHED = True


def create_gemini_client() -> genai.Client:
    """Create a Gemini SDK client with guarded cleanup."""

    patch_gemini_cleanup()
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
