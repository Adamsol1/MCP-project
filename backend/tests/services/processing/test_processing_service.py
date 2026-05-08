import json
import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.processing.processing_service import ProcessingService


@pytest.fixture
def mock_mcp_client():
    client = MagicMock()

    @asynccontextmanager
    async def mock_connect():
        yield client

    client.connect = mock_connect
    client.get_prompt = AsyncMock(return_value="System prompt text")
    return client


class TestProcess:
    @pytest.mark.asyncio
    async def test_injects_reasoning_from_thought_text_when_reasoning_is_empty(self, mock_mcp_client):
        # arrange
        with patch("src.services.processing.processing_service.create_tool_agent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.run = AsyncMock(return_value='{"findings": [], "reasoning": ""}')
            mock_agent.last_thought_text = "My internal reasoning process"
            MockAgent.return_value = mock_agent
            service = ProcessingService(mcp_client=mock_mcp_client)

            # act
            result = await service.process(collected_data="raw data", pir="pir question")

        # assert
        parsed = json.loads(result)
        assert parsed["reasoning"] == "My internal reasoning process"

    @pytest.mark.asyncio
    async def test_returns_raw_when_no_thought_text(self, mock_mcp_client):
        # arrange
        raw_response = '{"findings": [], "reasoning": "already has reasoning"}'
        with patch("src.services.processing.processing_service.create_tool_agent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.run = AsyncMock(return_value=raw_response)
            mock_agent.last_thought_text = ""
            MockAgent.return_value = mock_agent
            service = ProcessingService(mcp_client=mock_mcp_client)

            # act
            result = await service.process(collected_data="data", pir="pir")

        # assert
        assert result == raw_response

    @pytest.mark.asyncio
    async def test_returns_raw_string_when_response_is_not_json(self, mock_mcp_client):
        # arrange
        with patch("src.services.processing.processing_service.create_tool_agent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.run = AsyncMock(return_value="Not valid JSON output")
            mock_agent.last_thought_text = "Some thought text"
            MockAgent.return_value = mock_agent
            service = ProcessingService(mcp_client=mock_mcp_client)

            # act
            result = await service.process(collected_data="data", pir="pir")

        # assert
        assert result == "Not valid JSON output"

    @pytest.mark.asyncio
    async def test_does_not_overwrite_existing_reasoning(self, mock_mcp_client):
        # arrange
        with patch("src.services.processing.processing_service.create_tool_agent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.run = AsyncMock(return_value='{"findings": [], "reasoning": "existing reasoning"}')
            mock_agent.last_thought_text = "Thought text that should not overwrite"
            MockAgent.return_value = mock_agent
            service = ProcessingService(mcp_client=mock_mcp_client)

            # act
            result = await service.process(collected_data="data", pir="pir")

        # assert
        parsed = json.loads(result)
        assert parsed["reasoning"] == "existing reasoning"


class TestModifyProcessing:
    @pytest.mark.asyncio
    async def test_calls_agent_and_returns_result(self, mock_mcp_client):
        # arrange
        with patch("src.services.processing.processing_service.create_tool_agent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.run = AsyncMock(return_value='{"modified": true}')
            MockAgent.return_value = mock_agent
            service = ProcessingService(mcp_client=mock_mcp_client)

            # act
            result = await service.modify_processing(
                existing_result='{"original": true}',
                modifications="Add more detail about the threat actor",
            )

        # assert
        assert result == '{"modified": true}'

    @pytest.mark.asyncio
    async def test_passes_language_to_prompt(self, mock_mcp_client):
        # arrange
        with patch("src.services.processing.processing_service.create_tool_agent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.run = AsyncMock(return_value="result")
            MockAgent.return_value = mock_agent
            service = ProcessingService(mcp_client=mock_mcp_client)

            # act
            await service.modify_processing(
                existing_result="existing",
                modifications="changes",
                language="no",
            )

        # assert
        call_kwargs = mock_mcp_client.get_prompt.call_args
        assert call_kwargs[0][1]["language"] == "no"
