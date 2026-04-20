from src.services.llm_config import get_llm_config


def test_local_llm_defaults_use_expected_vllm_configuration(monkeypatch):
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
    ):
        monkeypatch.delenv(name, raising=False)

    config = get_llm_config()

    assert config.base_url == "http://127.0.0.1:8001/v1"
    assert config.api_key == "my-secret-key"
    assert config.model == "Qwen/Qwen2.5-7B-Instruct"


def test_local_llm_ignores_openai_environment_fallbacks(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "real-openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("VLLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("VLLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("VLLM_MODEL", raising=False)

    config = get_llm_config()

    assert config.base_url == "http://127.0.0.1:8001/v1"
    assert config.api_key == "my-secret-key"
    assert config.model == "Qwen/Qwen2.5-7B-Instruct"


def test_local_llm_can_still_be_overridden_with_llm_environment(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://llm.example/v1")
    monkeypatch.setenv("LLM_API_KEY", "override-key")
    monkeypatch.setenv("LLM_MODEL", "override-model")

    config = get_llm_config()

    assert config.base_url == "http://llm.example/v1"
    assert config.api_key == "override-key"
    assert config.model == "override-model"
