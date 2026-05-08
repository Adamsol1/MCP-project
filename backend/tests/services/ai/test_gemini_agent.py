import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from google.genai import types

from src.services.ai.gemini_agent import GeminiAgent, _json_schema_to_gemini


class TestJsonSchemaToGemini:
    def test_string_type(self):
        # arrange
        schema = {"type": "string", "description": "A string value"}

        # act
        result = _json_schema_to_gemini(schema)

        # assert
        assert result.type == types.Type.STRING
        assert result.description == "A string value"

    def test_integer_type(self):
        # arrange
        schema = {"type": "integer"}

        # act
        result = _json_schema_to_gemini(schema)

        # assert
        assert result.type == types.Type.INTEGER

    def test_object_with_properties(self):
        # arrange
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name"],
        }

        # act
        result = _json_schema_to_gemini(schema)

        # assert
        assert result.type == types.Type.OBJECT
        assert "name" in result.properties
        assert "age" in result.properties
        assert result.required == ["name"]

    def test_array_with_items(self):
        # arrange
        schema = {"type": "array", "items": {"type": "string"}}

        # act
        result = _json_schema_to_gemini(schema)

        # assert
        assert result.type == types.Type.ARRAY
        assert result.items is not None
        assert result.items.type == types.Type.STRING

    def test_unknown_type_defaults_to_string(self):
        # arrange
        schema = {"type": "unknown_type"}

        # act
        result = _json_schema_to_gemini(schema)

        # assert
        assert result.type == types.Type.STRING

    def test_empty_schema_defaults_to_string(self):
        # arrange
        schema = {}

        # act
        result = _json_schema_to_gemini(schema)

        # assert
        assert result.type == types.Type.STRING


def _make_text_response(text: str):
    part = MagicMock()
    part.function_call = None
    part.thought = False
    part.text = text

    candidate = MagicMock()
    candidate.content = MagicMock()
    candidate.content.parts = [part]
    candidate.finish_reason = "STOP"

    response = MagicMock()
    response.candidates = [candidate]
    return response


def _make_tool_call_response(tool_name: str, args: dict):
    tool_part = MagicMock()
    tool_part.function_call = MagicMock()
    tool_part.function_call.name = tool_name
    tool_part.function_call.args = args
    # Default MagicMocks return a MagicMock for any attribute access; set
    # `text` explicitly to None so the agent's max-rounds fallback (which
    # joins all parts whose text is not None) doesn't try to concatenate
    # a MagicMock and TypeError out before we can return.
    tool_part.text = None

    candidate = MagicMock()
    candidate.content = MagicMock()
    candidate.content.parts = [tool_part]

    response = MagicMock()
    response.candidates = [candidate]
    return response


@pytest.fixture
def mock_mcp_client():
    client = AsyncMock()
    client.list_tools = AsyncMock(return_value=[])
    return client


@pytest.fixture
def agent(mock_mcp_client):
    # gemini_agent constructs its SDK client via create_gemini_client(); patch
    # that helper rather than the underlying google.genai module so the agent
    # still goes through its real init code path.
    with patch("src.services.ai.gemini_agent.create_gemini_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        a = GeminiAgent(mcp_client=mock_mcp_client, max_tool_rounds=3)
        a.client = mock_client
        yield a


class TestGeminiAgentRun:
    @pytest.mark.asyncio
    async def test_returns_text_on_no_tool_calls(self, agent):
        # arrange
        agent.client.aio.models.generate_content = AsyncMock(
            return_value=_make_text_response("Final answer")
        )

        # act
        result = await agent.run(system_prompt="You are helpful", task="Answer this")

        # assert
        assert result == "Final answer"

    @pytest.mark.asyncio
    async def test_returns_empty_string_on_no_candidates(self, agent):
        # arrange
        response = MagicMock()
        response.candidates = []
        agent.client.aio.models.generate_content = AsyncMock(return_value=response)

        # act
        result = await agent.run(system_prompt="prompt", task="task")

        # assert
        assert result == ""

    @pytest.mark.asyncio
    async def test_returns_empty_string_when_candidate_content_is_none(self, agent):
        # arrange
        candidate = MagicMock()
        candidate.content = None
        candidate.finish_reason = "SAFETY"
        response = MagicMock()
        response.candidates = [candidate]
        agent.client.aio.models.generate_content = AsyncMock(return_value=response)

        # act
        result = await agent.run(system_prompt="prompt", task="task")

        # assert
        assert result == ""

    @pytest.mark.asyncio
    async def test_executes_tool_call_and_continues(self, agent):
        # arrange
        tool_response = _make_tool_call_response("search", {"query": "test"})
        text_response = _make_text_response("Done after tool")
        agent.client.aio.models.generate_content = AsyncMock(
            side_effect=[tool_response, text_response]
        )
        agent.mcp_client.call_tool = AsyncMock(return_value="search results")

        # act
        result = await agent.run(system_prompt="prompt", task="task")

        # assert
        assert result == "Done after tool"
        agent.mcp_client.call_tool.assert_called_once_with("search", {"query": "test"})

    @pytest.mark.asyncio
    async def test_reaches_max_rounds_and_returns_fallback(self, agent):
        # arrange — always returns a tool call, never finishes
        agent.client.aio.models.generate_content = AsyncMock(
            return_value=_make_tool_call_response("loop_tool", {})
        )
        agent.mcp_client.call_tool = AsyncMock(return_value="result")

        # act
        result = await agent.run(system_prompt="prompt", task="task")

        # assert
        assert "maximum tool iterations" in result or result == ""

    @pytest.mark.asyncio
    async def test_captures_thought_text(self, agent):
        # arrange
        thought_part = MagicMock()
        thought_part.function_call = None
        thought_part.thought = True
        thought_part.text = "My internal reasoning"

        text_part = MagicMock()
        text_part.function_call = None
        text_part.thought = False
        text_part.text = "Final response"

        candidate = MagicMock()
        candidate.content = MagicMock()
        candidate.content.parts = [thought_part, text_part]
        candidate.finish_reason = "STOP"

        response = MagicMock()
        response.candidates = [candidate]
        agent.client.aio.models.generate_content = AsyncMock(return_value=response)

        # act
        result = await agent.run(system_prompt="prompt", task="task")

        # assert
        assert result == "Final response"
        assert agent.last_thought_text == "My internal reasoning"

    @pytest.mark.asyncio
    async def test_handles_tool_error_gracefully(self, agent):
        # arrange
        tool_response = _make_tool_call_response("failing_tool", {})
        text_response = _make_text_response("Recovered after error")
        agent.client.aio.models.generate_content = AsyncMock(
            side_effect=[tool_response, text_response]
        )
        agent.mcp_client.call_tool = AsyncMock(side_effect=Exception("Tool failed"))

        # act
        result = await agent.run(system_prompt="prompt", task="task")

        # assert
        assert result == "Recovered after error"

    @pytest.mark.asyncio
    async def test_calls_status_tracker_on_tool_call(self, agent):
        # arrange
        tool_response = _make_tool_call_response("search", {"query": "test"})
        text_response = _make_text_response("Done")
        agent.client.aio.models.generate_content = AsyncMock(
            side_effect=[tool_response, text_response]
        )
        agent.mcp_client.call_tool = AsyncMock(return_value="result")
        mock_tracker = MagicMock()

        # act
        await agent.run(system_prompt="prompt", task="task", status_tracker=mock_tracker)

        # assert
        mock_tracker.record_tool_call.assert_called_once_with("search", {"query": "test"})


class TestGetToolDeclarations:
    @pytest.mark.asyncio
    async def test_returns_all_tools_when_no_filter(self, agent):
        # arrange
        agent.mcp_client.list_tools = AsyncMock(return_value=[
            {"name": "tool_a", "description": "Tool A", "inputSchema": {}},
            {"name": "tool_b", "description": "Tool B", "inputSchema": {}},
        ])

        # act
        result = await agent._get_tool_declarations(None)

        # assert
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_filters_by_allowed_names(self, agent):
        # arrange
        agent.mcp_client.list_tools = AsyncMock(return_value=[
            {"name": "tool_a", "description": "Tool A", "inputSchema": {}},
            {"name": "tool_b", "description": "Tool B", "inputSchema": {}},
        ])

        # act
        result = await agent._get_tool_declarations({"tool_a"})

        # assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_when_filter_matches_nothing(self, agent):
        # arrange
        agent.mcp_client.list_tools = AsyncMock(return_value=[
            {"name": "tool_a", "description": "Tool A", "inputSchema": {}},
        ])

        # act
        result = await agent._get_tool_declarations({"unknown_tool"})

        # assert
        assert len(result) == 0


class TestFetchUrlSummaries:
    @pytest.mark.asyncio
    async def test_returns_empty_list_for_no_urls(self, agent):
        # arrange — no setup needed

        # act
        result = await agent.fetch_url_summaries([], pir="test", perspectives=["neutral"])

        # assert
        assert result == []

    @pytest.mark.asyncio
    async def test_parses_valid_page_summaries(self, agent):
        # arrange
        summary_json = json.dumps({
            "page_summaries": [{
                "url": "https://example.com",
                "title": "Test Article",
                "summary": "Important findings about security threats.",
                "apa_citation": "Author, A. (2025). Test. Example.",
                "author": "Author, A.",
                "date": "2025-01-01",
                "publisher": "Example",
            }]
        })
        part = MagicMock()
        part.text = summary_json
        candidate = MagicMock()
        candidate.content = MagicMock()
        candidate.content.parts = [part]
        response = MagicMock()
        response.candidates = [candidate]
        agent.client.aio.models.generate_content = AsyncMock(return_value=response)

        # act
        result = await agent.fetch_url_summaries(
            ["https://example.com"], pir="test", perspectives=["neutral"]
        )

        # assert
        assert len(result) == 1
        assert result[0]["source"] == "fetch_page"
        assert result[0]["resource_id"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_skips_inaccessible_pages(self, agent):
        # arrange
        summary_json = json.dumps({
            "page_summaries": [{
                "url": "https://paywalled.com",
                "title": "Test",
                "summary": "This page is not accessible due to a paywall.",
            }]
        })
        part = MagicMock()
        part.text = summary_json
        candidate = MagicMock()
        candidate.content = MagicMock()
        candidate.content.parts = [part]
        response = MagicMock()
        response.candidates = [candidate]
        agent.client.aio.models.generate_content = AsyncMock(return_value=response)

        # act
        result = await agent.fetch_url_summaries(
            ["https://paywalled.com"], pir="test", perspectives=["neutral"]
        )

        # assert
        assert result == []

    @pytest.mark.asyncio
    async def test_handles_blocked_response_gracefully(self, agent):
        # arrange
        response = MagicMock()
        response.candidates = []
        agent.client.aio.models.generate_content = AsyncMock(return_value=response)

        # act
        result = await agent.fetch_url_summaries(
            ["https://example.com"], pir="test", perspectives=["neutral"]
        )

        # assert
        assert result == []
