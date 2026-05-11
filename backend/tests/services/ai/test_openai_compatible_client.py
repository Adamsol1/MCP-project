import json

import httpx
import pytest
import respx

from src.services.ai.llm_config import LLMConfig
from src.services.ai.openai_compatible_client import OpenAICompatibleClient


@pytest.mark.asyncio
@respx.mock
async def test_chat_retries_without_tools_when_vllm_rejects_tool_choice():
    client = OpenAICompatibleClient(
        config=LLMConfig(
            base_url="http://llm.test/v1",
            api_key="test-key",
            model="test-model",
            timeout_seconds=5,
            temperature=0.7,
            max_completion_tokens=512,
            enable_thinking=False,
        )
    )
    route = respx.post("http://llm.test/v1/chat/completions").mock(
        side_effect=[
            httpx.Response(
                400,
                json={
                    "error": {
                        "message": '"auto" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set',
                    }
                },
            ),
            httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"role": "assistant", "content": "ok"}}
                    ]
                },
            ),
        ]
    )

    result = await client.chat(
        [{"role": "user", "content": "hello"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "noop",
                    "description": "No-op",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
    )

    first_request = json.loads(route.calls[0].request.content)
    second_request = json.loads(route.calls[1].request.content)

    assert result["content"] == "ok"
    assert route.call_count == 2
    assert first_request["tool_choice"] == "auto"
    assert first_request["temperature"] == 0.7
    assert first_request["max_completion_tokens"] == 512
    assert first_request["chat_template_kwargs"] == {"enable_thinking": False}
    assert "tools" in first_request
    assert "tool_choice" not in second_request
    assert "tools" not in second_request


@pytest.mark.asyncio
@respx.mock
async def test_chat_retries_without_tools_when_provider_disconnects_on_tools():
    OpenAICompatibleClient._tools_supported = True
    client = OpenAICompatibleClient(
        config=LLMConfig(
            base_url="http://llm.test/v1",
            api_key="test-key",
            model="test-model",
            timeout_seconds=5,
            temperature=None,
            max_completion_tokens=None,
            enable_thinking=None,
        )
    )
    route = respx.post("http://llm.test/v1/chat/completions").mock(
        side_effect=[
            httpx.RemoteProtocolError("Server disconnected without sending a response."),
            httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"role": "assistant", "content": "ok"}}
                    ]
                },
            ),
        ]
    )

    result = await client.chat(
        [{"role": "user", "content": "hello"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "noop",
                    "description": "No-op",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
    )

    first_request = json.loads(route.calls[0].request.content)
    second_request = json.loads(route.calls[1].request.content)

    assert result["content"] == "ok"
    assert "tools" in first_request
    assert "tools" not in second_request


@pytest.mark.asyncio
@respx.mock
async def test_chat_normalizes_local_model_decoding_artifacts():
    client = OpenAICompatibleClient(
        config=LLMConfig(
            base_url="http://llm.test/v1",
            api_key="test-key",
            model="test-model",
            timeout_seconds=5,
            temperature=None,
            max_completion_tokens=None,
            enable_thinking=None,
        )
    )
    respx.post("http://llm.test/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "\u010a<think>hidden</think>\u010aHello\u0120world",
                        }
                    }
                ]
            },
        )
    )

    result = await client.chat([{"role": "user", "content": "hello"}])

    assert result["content"] == "Hello world"


@pytest.mark.asyncio
@respx.mock
async def test_chat_raises_clear_error_when_local_endpoint_is_unreachable():
    client = OpenAICompatibleClient(
        config=LLMConfig(
            base_url="http://llm.test/v1",
            api_key="test-key",
            model="test-model",
            timeout_seconds=5,
            temperature=None,
            max_completion_tokens=None,
            enable_thinking=None,
        )
    )
    respx.post("http://llm.test/v1/chat/completions").mock(
        side_effect=httpx.ConnectError("failed")
    )

    with pytest.raises(RuntimeError, match="Could not connect"):
        await client.chat([{"role": "user", "content": "hello"}])
