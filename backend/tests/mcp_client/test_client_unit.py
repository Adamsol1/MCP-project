import pytest
from unittest.mock import AsyncMock, MagicMock

from mcp.types import TextContent

from src.mcp_client.client import MCPClient, _get_tlp_level


class TestGetTlpLevel:
    def test_detects_tlp_red(self):
        # arrange
        header = "TLP:RED Some classified content here"

        # act
        result = _get_tlp_level(header)

        # assert
        assert result == "TLP:RED"

    def test_detects_tlp_amber_strict_before_amber(self):
        # arrange
        header = "TLP:AMBER+STRICT restricted content"

        # act
        result = _get_tlp_level(header)

        # assert
        assert result == "TLP:AMBER+STRICT"

    def test_detects_tlp_amber(self):
        # arrange
        header = "TLP:AMBER limited distribution"

        # act
        result = _get_tlp_level(header)

        # assert
        assert result == "TLP:AMBER"

    def test_detects_tlp_green(self):
        # arrange
        header = "TLP:GREEN community sharing"

        # act
        result = _get_tlp_level(header)

        # assert
        assert result == "TLP:GREEN"

    def test_returns_none_when_no_tlp_marking(self):
        # arrange
        header = "Regular content with no classification markings"

        # act
        result = _get_tlp_level(header)

        # assert
        assert result is None

    def test_is_case_insensitive(self):
        # arrange
        header = "tlp:red content"

        # act
        result = _get_tlp_level(header)

        # assert
        assert result == "TLP:RED"


class TestStripFences:
    def test_strips_backtick_code_block(self):
        # arrange
        text = "```json\n{}\n```"

        # act
        result = MCPClient._strip_fences(text)

        # assert
        assert result == "{}"

    def test_leaves_plain_text_unchanged(self):
        # arrange
        text = "plain text response"

        # act
        result = MCPClient._strip_fences(text)

        # assert
        assert result == "plain text response"

    def test_strips_surrounding_whitespace(self):
        # arrange
        text = "  hello  "

        # act
        result = MCPClient._strip_fences(text)

        # assert
        assert result == "hello"


class TestCallTool:
    @pytest.mark.asyncio
    async def test_raises_runtime_error_when_not_connected(self):
        # arrange
        client = MCPClient()

        # act / assert
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.call_tool("my_tool")

    @pytest.mark.asyncio
    async def test_parses_json_response(self):
        # arrange
        client = MCPClient()
        mock_result = MagicMock()
        mock_result.content = [TextContent(type="text", text='{"result": "ok"}')]
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)
        client.session = mock_session

        # act
        result = await client.call_tool("my_tool", {"arg": "val"})

        # assert
        assert result == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_returns_raw_text_when_response_is_not_json(self):
        # arrange
        client = MCPClient()
        mock_result = MagicMock()
        mock_result.content = [TextContent(type="text", text="plain text response")]
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)
        client.session = mock_session

        # act
        result = await client.call_tool("my_tool")

        # assert
        assert result == "plain text response"

    @pytest.mark.asyncio
    async def test_raises_value_error_on_empty_content(self):
        # arrange
        client = MCPClient()
        mock_result = MagicMock()
        mock_result.content = []
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)
        client.session = mock_session

        # act / assert
        with pytest.raises(ValueError, match="empty content"):
            await client.call_tool("my_tool")


class TestListTools:
    @pytest.mark.asyncio
    async def test_raises_runtime_error_when_not_connected(self):
        # arrange
        client = MCPClient()

        # act / assert
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.list_tools()


class TestGetPrompt:
    @pytest.mark.asyncio
    async def test_raises_runtime_error_when_not_connected(self):
        # arrange
        client = MCPClient()

        # act / assert
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.get_prompt("my_prompt")


class TestMaybeElicitClassified:
    @pytest.mark.asyncio
    async def test_returns_false_when_no_elicitation_callback(self):
        # arrange
        client = MCPClient()

        # act
        result = await client._maybe_elicit_classified("TLP:RED classified content")

        # assert
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_non_restricted_tlp(self):
        # arrange
        callback = AsyncMock(return_value="Fortsett med Gemini")
        client = MCPClient(elicitation_callback=callback)

        # act
        result = await client._maybe_elicit_classified("TLP:GREEN public content")

        # assert
        assert result is False
        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_fires_callback_for_tlp_red_content(self):
        # arrange
        callback = AsyncMock(return_value="Fortsett med Gemini")
        client = MCPClient(elicitation_callback=callback)

        # act
        result = await client._maybe_elicit_classified("TLP:RED classified content here")

        # assert
        assert result is False
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_true_when_user_chooses_local_llm(self):
        # arrange
        callback = AsyncMock(return_value="Bytt til lokal LLM")
        client = MCPClient(elicitation_callback=callback)

        # act
        result = await client._maybe_elicit_classified("TLP:RED top secret content")

        # assert
        assert result is True

    @pytest.mark.asyncio
    async def test_callback_fires_only_once_across_multiple_calls(self):
        # arrange
        callback = AsyncMock(return_value="Fortsett med Gemini")
        client = MCPClient(elicitation_callback=callback)

        # act
        await client._maybe_elicit_classified("TLP:RED first call")
        await client._maybe_elicit_classified("TLP:RED second call")

        # assert
        callback.assert_called_once()
