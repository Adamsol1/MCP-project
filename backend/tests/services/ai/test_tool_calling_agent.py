import json

import pytest

from src.services.ai.tool_calling_agent import ToolCallingAgent


class FakeMCPClient:
    def __init__(self):
        self.calls = []

    async def list_tools(self):
        return [
            {
                "name": "google_search",
                "description": "Search the web",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            }
        ]

    async def call_tool(self, name, args):
        self.calls.append((name, args))
        return {"results": [{"title": "Example", "url": "https://example.com"}]}


class FakeClient:
    def __init__(self):
        self.calls = []

    async def chat(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        if len(self.calls) == 1:
            raise RuntimeError("The configured local LLM endpoint does not support tool calling.")
        if len(self.calls) == 2:
            return {
                "content": json.dumps(
                    {
                        "tool_calls": [
                            {
                                "name": "google_search",
                                "arguments": {"query": "Norway cyber threat"},
                            }
                        ]
                    }
                )
            }
        return {
            "content": json.dumps(
                {
                    "final": {
                        "collected_data": [
                            {"source": "google_search", "content": "Example result"}
                        ]
                    }
                }
            )
        }


@pytest.mark.asyncio
async def test_falls_back_to_text_tool_loop_when_native_tools_are_unsupported():
    mcp_client = FakeMCPClient()
    agent = ToolCallingAgent(mcp_client=mcp_client)
    fake_client = FakeClient()
    agent.client = fake_client

    result = await agent.run(
        system_prompt="Collect evidence.",
        task="Search for relevant evidence.",
        allowed_tool_names={"google_search"},
    )

    assert json.loads(result)["collected_data"][0]["source"] == "google_search"
    assert mcp_client.calls == [("google_search", {"query": "Norway cyber threat"})]
    assert fake_client.calls[0][1]["require_tools"] is True
    assert "tools" in fake_client.calls[0][1]
    assert fake_client.calls[1][1] == {}
