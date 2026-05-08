import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.ai.llm_service import LLMService, _repair_json


class TestRepairJson:
    def test_fixes_typographic_double_quotes(self):
        # arrange
        text = '{"key": “value”}'

        # act
        result = _repair_json(text)

        # assert
        assert json.loads(result) == {"key": "value"}

    def test_fixes_invalid_escape_sequences(self):
        # arrange
        text = r'{"key": "it\'s here"}'

        # act
        result = _repair_json(text)

        # assert
        assert "\\'" not in result

    def test_fixes_trailing_comma_before_brace(self):
        # arrange
        text = '{"key": "value",}'

        # act
        result = _repair_json(text)

        # assert
        assert json.loads(result) == {"key": "value"}

    def test_fixes_trailing_comma_before_bracket(self):
        # arrange
        text = '{"arr": [1, 2, 3,]}'

        # act
        result = _repair_json(text)

        # assert
        assert json.loads(result) == {"arr": [1, 2, 3]}

    def test_handles_empty_string(self):
        # arrange
        text = ""

        # act
        result = _repair_json(text)

        # assert
        assert result == ""

    def test_valid_json_passes_through_unchanged(self):
        # arrange
        text = '{"key": "value", "num": 42}'

        # act
        result = _repair_json(text)

        # assert
        assert json.loads(result) == {"key": "value", "num": 42}


class TestStripFences:
    def test_strips_json_code_fence(self):
        # arrange
        text = '```json\n{"key": "value"}\n```'

        # act
        result = LLMService._strip_fences(text)

        # assert
        assert result == '{"key": "value"}'

    def test_strips_plain_code_fence(self):
        # arrange
        text = '```\n{"key": "value"}\n```'

        # act
        result = LLMService._strip_fences(text)

        # assert
        assert result == '{"key": "value"}'

    def test_extracts_json_object_from_prose(self):
        # arrange
        text = 'Here is the result: {"key": "value"} done.'

        # act
        result = LLMService._strip_fences(text)

        # assert
        assert '{"key": "value"}' in result

    def test_returns_plain_text_when_no_braces(self):
        # arrange
        text = "no braces here"

        # act
        result = LLMService._strip_fences(text)

        # assert
        assert result == "no braces here"

    def test_strips_leading_trailing_whitespace(self):
        # arrange
        text = '  {"k": 1}  '

        # act
        result = LLMService._strip_fences(text)

        # assert
        assert result == '{"k": 1}'


@pytest.fixture
def llm_service():
    """Yield an LLMService whose provider is fully mocked.

    Post-refactor LLMService delegates to `provider.generate_text` /
    `provider.generate_json_text`, so we mock the provider directly rather
    than reaching into the Gemini SDK. Tests below set up the mock per case
    via `llm_service.provider.generate_text = AsyncMock(...)`.
    """
    fake_provider = MagicMock()
    fake_provider.model = "test-model"
    fake_provider.generate_text = AsyncMock()
    fake_provider.generate_json_text = AsyncMock()
    with patch(
        "src.services.ai.llm_service.get_provider", return_value=fake_provider
    ):
        service = LLMService()
        yield service


class TestGenerateText:
    @pytest.mark.asyncio
    async def test_returns_response_text(self, llm_service):
        llm_service.provider.generate_text.return_value = "Hello, world!"
        result = await llm_service.generate_text("test prompt")
        assert result == "Hello, world!"

    @pytest.mark.asyncio
    async def test_raises_on_empty_response(self, llm_service):
        llm_service.provider.generate_text.side_effect = ValueError(
            "Model test-model returned empty response"
        )
        with pytest.raises(ValueError, match="empty response"):
            await llm_service.generate_text("test prompt")

    @pytest.mark.asyncio
    async def test_raises_on_none_text(self, llm_service):
        llm_service.provider.generate_text.side_effect = ValueError(
            "Model test-model returned empty response"
        )
        with pytest.raises(ValueError):
            await llm_service.generate_text("test prompt")


class TestGenerateJson:
    @pytest.mark.asyncio
    async def test_parses_clean_json(self, llm_service):
        llm_service.provider.generate_json_text.return_value = '{"key": "value"}'
        result = await llm_service.generate_json("test prompt")
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_strips_code_fences_before_parsing(self, llm_service):
        llm_service.provider.generate_json_text.return_value = (
            '```json\n{"key": "value"}\n```'
        )
        result = await llm_service.generate_json("test prompt")
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_falls_back_to_repair_on_trailing_comma(self, llm_service):
        llm_service.provider.generate_json_text.return_value = '{"key": "value",}'
        result = await llm_service.generate_json("test prompt")
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_raises_on_completely_unparseable(self, llm_service):
        llm_service.provider.generate_json_text.return_value = (
            "this is just plain text not json at all"
        )
        with pytest.raises(json.JSONDecodeError):
            await llm_service.generate_json("test prompt")
