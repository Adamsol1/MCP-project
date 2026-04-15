import json

import httpx
import pytest
import respx

from src.services.llm_config import LLMConfig
from src.services.openai_compatible_client import OpenAICompatibleClient


@pytest.mark.asyncio
@respx.mock
async def test_chat_retries_without_tools_when_vllm_rejects_tool_choice():
    client = OpenAICompatibleClient(
        config=LLMConfig(
            base_url="http://llm.test/v1",
            api_key="test-key",
            model="test-model",
            timeout_seconds=5,
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
    assert "tools" in first_request
    assert "tool_choice" not in second_request
    assert "tools" not in second_request
