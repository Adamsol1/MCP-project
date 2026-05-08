"""Runtime configuration for the app's LLM provider."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

DEFAULT_LLM_BASE_URL = "http://127.0.0.1:8001/v1"
DEFAULT_LLM_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_LLM_TIMEOUT_SECONDS = 180
DEFAULT_LLM_TEMPERATURE = 0.7
DEFAULT_LLM_MAX_COMPLETION_TOKENS: int | None = None
# Default is None (= don't send `chat_template_kwargs.enable_thinking`).
# Only Qwen / Llama-thinking style endpoints understand this knob; sending it
# to DeepSeek / OpenAI / Anthropic-compatible endpoints either errors or is
# silently dropped. Users who actually need it set LLM_ENABLE_THINKING=true|false.
DEFAULT_LLM_ENABLE_THINKING: bool | None = None
DEFAULT_LLM_PROVIDER = "gemini"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

_request_llm_provider: ContextVar[str | None] = ContextVar(
    "request_llm_provider",
    default=None,
)


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _normalize_openai_base_url(base_url: str) -> str:
    base_url = base_url.rstrip("/")
    if base_url.endswith("/v1"):
        return base_url
    return f"{base_url}/v1"


@dataclass(frozen=True)
class LLMConfig:
    """OpenAI-compatible chat-completions configuration."""

    base_url: str
    api_key: str | None
    model: str
    timeout_seconds: int
    temperature: float | None
    max_completion_tokens: int | None
    enable_thinking: bool | None


def get_llm_config(model: str | None = None) -> LLMConfig:
    """Return the active LLM configuration.

    Local LLM access uses an OpenAI-compatible endpoint configured with LLM_*.
    No API key is sent unless LLM_API_KEY is explicitly set.
    """

    timeout_raw = os.getenv("LLM_TIMEOUT_SECONDS")
    try:
        timeout_seconds = (
            int(timeout_raw) if timeout_raw else DEFAULT_LLM_TIMEOUT_SECONDS
        )
    except ValueError:
        timeout_seconds = DEFAULT_LLM_TIMEOUT_SECONDS

    temperature_raw = os.getenv("LLM_TEMPERATURE")
    try:
        temperature = (
            float(temperature_raw) if temperature_raw else DEFAULT_LLM_TEMPERATURE
        )
    except ValueError:
        temperature = DEFAULT_LLM_TEMPERATURE

    max_tokens_raw = os.getenv("LLM_MAX_COMPLETION_TOKENS")
    if max_tokens_raw and max_tokens_raw.strip().lower() not in {
        "none",
        "null",
        "unlimited",
    }:
        try:
            configured_max_tokens = int(max_tokens_raw)
            max_completion_tokens = (
                configured_max_tokens if configured_max_tokens > 0 else None
            )
        except ValueError:
            max_completion_tokens = DEFAULT_LLM_MAX_COMPLETION_TOKENS
    else:
        max_completion_tokens = DEFAULT_LLM_MAX_COMPLETION_TOKENS

    enable_thinking_raw = os.getenv("LLM_ENABLE_THINKING")
    if enable_thinking_raw is None:
        enable_thinking = DEFAULT_LLM_ENABLE_THINKING
    else:
        enable_thinking = enable_thinking_raw.strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    return LLMConfig(
        base_url=_normalize_openai_base_url(
            os.getenv("LLM_BASE_URL") or DEFAULT_LLM_BASE_URL
        ),
        api_key=os.getenv("LLM_API_KEY") or None,
        model=model or os.getenv("LLM_MODEL") or DEFAULT_LLM_MODEL,
        timeout_seconds=timeout_seconds,
        temperature=temperature,
        max_completion_tokens=max_completion_tokens,
        enable_thinking=enable_thinking,
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

    provider = _request_llm_provider.get() or (
        _first_env("LLM_PROVIDER", "AI_PROVIDER", "MODEL_PROVIDER")
        or DEFAULT_LLM_PROVIDER
    )
    provider = provider.strip().lower()
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
        raise ValueError(
            f"Unsupported LLM_PROVIDER '{provider}'. Use one of: {allowed}"
        )
    return aliases[provider]


def get_default_model_name() -> str:
    if get_llm_provider() == "gemini":
        return get_default_gemini_model()
    return get_default_llm_model()


@contextmanager
def request_llm_provider(provider: str | None) -> Iterator[None]:
    """Temporarily override the provider for the current request/task."""

    if provider is None:
        yield
        return

    normalized_provider = provider.strip().lower()
    token = _request_llm_provider.set(normalized_provider)
    try:
        # Validate early so API requests fail before any model call starts.
        get_llm_provider()
        yield
    finally:
        _request_llm_provider.reset(token)
