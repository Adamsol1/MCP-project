"""Runtime configuration for the app's LLM provider."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_LLM_BASE_URL = "http://127.0.0.1:8000/v1"
DEFAULT_LLM_API_KEY = "my-secret-key"
DEFAULT_LLM_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_LLM_TIMEOUT_SECONDS = 180
DEFAULT_LLM_PROVIDER = "local"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


@dataclass(frozen=True)
class LLMConfig:
    """OpenAI-compatible chat-completions configuration."""

    base_url: str
    api_key: str | None
    model: str
    timeout_seconds: int


def get_llm_config(model: str | None = None) -> LLMConfig:
    """Return the active LLM configuration.

    The defaults point at the user's local vLLM server. Environment variables can
    still override them without changing app code.
    """

    timeout_raw = _first_env("LLM_TIMEOUT_SECONDS", "VLLM_TIMEOUT_SECONDS")
    try:
        timeout_seconds = (
            int(timeout_raw) if timeout_raw else DEFAULT_LLM_TIMEOUT_SECONDS
        )
    except ValueError:
        timeout_seconds = DEFAULT_LLM_TIMEOUT_SECONDS

    return LLMConfig(
        base_url=_first_env("LLM_BASE_URL", "VLLM_BASE_URL", "OPENAI_BASE_URL")
        or DEFAULT_LLM_BASE_URL,
        api_key=_first_env("LLM_API_KEY", "VLLM_API_KEY", "OPENAI_API_KEY")
        or DEFAULT_LLM_API_KEY,
        model=model
        or _first_env("LLM_MODEL", "VLLM_MODEL", "OPENAI_MODEL")
        or DEFAULT_LLM_MODEL,
        timeout_seconds=timeout_seconds,
    )


def get_default_llm_model() -> str:
    return get_llm_config().model


def get_default_gemini_model() -> str:
    return (
        _first_env("GEMINI_MODEL", "GEMINI_API_MODEL", "GOOGLE_MODEL")
        or DEFAULT_GEMINI_MODEL
    )


def get_llm_provider() -> str:
    """Return the active AI provider: "local" or "gemini".

    local:  OpenAI-compatible endpoint, configured by LLM_BASE_URL/LLM_MODEL.
    gemini: Google Gemini API, configured by GEMINI_API_KEY/GEMINI_MODEL.
    """

    provider = (
        _first_env("LLM_PROVIDER", "AI_PROVIDER", "MODEL_PROVIDER")
        or DEFAULT_LLM_PROVIDER
    ).strip().lower()
    aliases = {
        "local": "local",
        "local_llm": "local",
        "localllm": "local",
        "openai-compatible": "local",
        "openai_compatible": "local",
        "vllm": "local",
        "gemini": "gemini",
        "gemini-api": "gemini",
        "gemini_api": "gemini",
        "google": "gemini",
    }
    if provider not in aliases:
        allowed = ", ".join(sorted(set(aliases.values())))
        raise ValueError(f"Unsupported LLM_PROVIDER '{provider}'. Use one of: {allowed}")
    return aliases[provider]


def get_default_model_name() -> str:
    if get_llm_provider() == "gemini":
        return get_default_gemini_model()
    return get_default_llm_model()
