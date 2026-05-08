from src.services.ai.llm_config import get_llm_config, get_llm_provider


def test_local_llm_defaults_use_expected_configuration(monkeypatch):
    for name in (
        "LLM_BASE_URL",
        "VLLM_BASE_URL",
        "OPENAI_BASE_URL",
        "LLM_API_KEY",
        "VLLM_API_KEY",
        "OPENAI_API_KEY",
        "LLM_MODEL",
        "VLLM_MODEL",
        "OPENAI_MODEL",
        "LLM_PROVIDER",
        "AI_PROVIDER",
        "MODEL_PROVIDER",
        "LLM_ENABLE_THINKING",
        "LLM_TIMEOUT_SECONDS",
        "LLM_TEMPERATURE",
        "LLM_MAX_COMPLETION_TOKENS",
    ):
        monkeypatch.delenv(name, raising=False)

    config = get_llm_config()

    assert config.base_url == "http://127.0.0.1:8001/v1"
    assert config.api_key is None
    assert config.model == "Qwen/Qwen2.5-7B-Instruct"
    assert config.timeout_seconds == 180
    assert config.temperature == 0.7
    assert config.max_completion_tokens == 512
    assert config.enable_thinking is None
    assert get_llm_provider() == "gemini"


def test_local_llm_ignores_non_llm_environment_fallbacks(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "real-openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.example/v1")
    monkeypatch.setenv("VLLM_API_KEY", "vllm-key")
    monkeypatch.setenv("VLLM_MODEL", "vllm-model")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    config = get_llm_config()

    assert config.base_url == "http://127.0.0.1:8001/v1"
    assert config.api_key is None
    assert config.model == "Qwen/Qwen2.5-7B-Instruct"


def test_provider_can_be_overridden_with_environment(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "local")

    assert get_llm_provider() == "local"


def test_local_llm_can_still_be_overridden_with_llm_environment(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://llm.example")
    monkeypatch.setenv("LLM_API_KEY", "override-key")
    monkeypatch.setenv("LLM_MODEL", "override-model")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "240")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.2")
    monkeypatch.setenv("LLM_MAX_COMPLETION_TOKENS", "1024")
    monkeypatch.setenv("LLM_ENABLE_THINKING", "true")

    config = get_llm_config()

    assert config.base_url == "http://llm.example/v1"
    assert config.api_key == "override-key"
    assert config.model == "override-model"
    assert config.timeout_seconds == 240
    assert config.temperature == 0.2
    assert config.max_completion_tokens == 1024
    assert config.enable_thinking is True


def test_local_llm_keeps_explicit_openai_v1_base_url(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://llm.example/v1")

    config = get_llm_config()

    assert config.base_url == "http://llm.example/v1"


def test_invalid_llm_numeric_settings_fall_back_to_defaults(monkeypatch):
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "not-a-number")
    monkeypatch.setenv("LLM_TEMPERATURE", "not-a-float")
    monkeypatch.setenv("LLM_MAX_COMPLETION_TOKENS", "not-an-int")

    config = get_llm_config()

    assert config.timeout_seconds == 180
    assert config.temperature == 0.7
    assert config.max_completion_tokens == 512
