import json
import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

from src.models.dialogue import DialogueContext, Perspective
from src.services.direction.dialogue_service import DialogueService


def _make_full_context():
    ctx = DialogueContext()
    ctx.scope = "Identify cyber threats"
    ctx.timeframe = "last 6 months"
    ctx.target_entities = ["Norway telecom"]
    ctx.threat_actors = ["APT28"]
    ctx.priority_focus = "Critical infrastructure"
    ctx.perspectives = [Perspective.NORWAY]
    return ctx


class TestIdentifyMissingContext:
    def setup_method(self):
        self.service = DialogueService(mcp_client=MagicMock(), ai_orchestrator=MagicMock())

    def test_all_fields_missing_returns_all_field_names(self):
        # arrange
        ctx = DialogueContext()

        # act
        missing = self.service._identify_missing_context(ctx)

        # assert
        assert "scope" in missing
        assert "timeframe" in missing
        assert "target_entities" in missing
        assert "threat_actors" in missing
        assert "priority_focus" in missing

    def test_filled_fields_are_not_in_missing_list(self):
        # arrange
        ctx = DialogueContext()
        ctx.scope = "Test scope"
        ctx.timeframe = "last 3 months"

        # act
        missing = self.service._identify_missing_context(ctx)

        # assert
        assert "scope" not in missing
        assert "timeframe" not in missing

    def test_fully_filled_context_returns_empty_list(self):
        # arrange
        ctx = _make_full_context()

        # act
        missing = self.service._identify_missing_context(ctx)

        # assert
        assert missing == []

    def test_only_missing_fields_are_returned(self):
        # arrange
        ctx = DialogueContext()
        ctx.scope = "Scope set"

        # act
        missing = self.service._identify_missing_context(ctx)

        # assert
        assert "scope" not in missing
        assert len(missing) == 4


class TestParseJson:
    def test_parses_clean_json_string(self):
        # arrange
        raw = '{"key": "value", "num": 42}'

        # act
        result = DialogueService._parse_json(raw)

        # assert
        assert result == {"key": "value", "num": 42}

    def test_strips_json_code_fence_before_parsing(self):
        # arrange
        raw = '```json\n{"key": "value"}\n```'

        # act
        result = DialogueService._parse_json(raw)

        # assert
        assert result == {"key": "value"}

    def test_extracts_json_from_preamble_text(self):
        # arrange
        raw = 'Here is my response: {"question": "What next?"}'

        # act
        result = DialogueService._parse_json(raw)

        # assert
        assert result["question"] == "What next?"

    def test_raises_value_error_on_empty_string(self):
        # arrange
        raw = ""

        # act / assert
        with pytest.raises(ValueError, match="empty response"):
            DialogueService._parse_json(raw)

    def test_raises_value_error_on_pure_prose(self):
        # arrange
        raw = "This is just plain prose with no JSON anywhere inside it."

        # act / assert
        with pytest.raises(ValueError, match="Could not parse JSON"):
            DialogueService._parse_json(raw)

    def test_parses_json_after_thinking_preamble(self):
        # arrange
        raw = "Let me think about this... [reasoning] ...\n\n```json\n{\"result\": true}\n```"

        # act
        result = DialogueService._parse_json(raw)

        # assert
        assert result == {"result": True}

    def test_parses_whitespace_only_raises_error(self):
        # arrange
        raw = "   \n  "

        # act / assert
        with pytest.raises(ValueError):
            DialogueService._parse_json(raw)


class TestFetchRelevantResources:
    @pytest.mark.asyncio
    async def test_prefetches_keyword_matches_by_priority_and_skips_failed_resource(self):
        # arrange
        ctx = _make_full_context()
        ctx.priority_focus = "telecom resilience and identity access"
        index = [
            {
                "id": "low-priority",
                "uri": "knowledge://low",
                "keywords": ["telecom"],
                "priority": 20,
            },
            {
                "id": "high-priority",
                "uri": "knowledge://high",
                "keywords": ["identity"],
                "priority": 1,
            },
            {
                "id": "broken",
                "uri": "knowledge://broken",
                "keywords": ["resilience"],
                "priority": 2,
            },
        ]

        async def read_resource(uri):
            if uri == "knowledge://index":
                return json.dumps(index)
            if uri == "knowledge://broken":
                raise RuntimeError("missing resource")
            return f"content:{uri}"

        mock_client = MagicMock()
        mock_client.read_resource = AsyncMock(side_effect=read_resource)
        service = DialogueService(mcp_client=mock_client, ai_orchestrator=MagicMock())

        # act
        result = await service._fetch_relevant_resources(ctx)

        # assert
        assert "## Background Knowledge" in result
        assert result.index("high-priority") < result.index("low-priority")
        assert "content:knowledge://high" in result
        assert "content:knowledge://low" in result
        assert "content:knowledge://broken" not in result


class TestGeneratePir:
    @pytest.mark.asyncio
    async def test_enriches_sources_with_citations_and_uses_thought_reasoning(self):
        # arrange
        ctx = _make_full_context()
        ctx.perspectives = [Perspective.US, Perspective.NORWAY]
        index = [
            {
                "id": "doc-1",
                "keywords": ["telecom"],
                "uri": "knowledge://doc-1",
                "citation": "Telecom Report 2026",
            }
        ]

        mock_client = MagicMock()

        @asynccontextmanager
        async def mock_connect():
            yield mock_client

        mock_client.connect = mock_connect
        mock_client.get_prompt = AsyncMock(return_value="pir prompt")
        mock_client.read_resource = AsyncMock(return_value=json.dumps(index))

        with pytest.MonkeyPatch().context():
            from unittest.mock import patch

            with patch("src.services.direction.dialogue_service.create_tool_agent") as MockAgent:
                mock_agent = MagicMock()
                mock_agent.last_thought_text = "Reasoned from telecom targeting evidence."
                mock_agent.run = AsyncMock(
                    return_value=json.dumps(
                        {
                            "pirs": [{"question": "What access is being developed?"}],
                            "sources": [{"id": "doc-1"}],
                            "reasoning": "",
                        }
                    )
                )
                MockAgent.return_value = mock_agent
                service = DialogueService(
                    mcp_client=mock_client,
                    ai_orchestrator=MagicMock(),
                )

                # act
                result = await service.generate_pir(ctx, language="en")

        # assert
        assert result["reasoning"] == "Reasoned from telecom targeting evidence."
        assert result["sources"][0]["citation"] == "Telecom Report 2026"
        prompt_args = mock_client.get_prompt.await_args.args[1]
        assert prompt_args["background_knowledge"]
        assert json.loads(prompt_args["perspectives"]) == ["us", "norway"]


class TestGenerationMethods:
    @pytest.mark.asyncio
    async def test_generate_clarifying_question_forces_insufficient_when_context_missing(self):
        # arrange
        ctx = DialogueContext()
        ctx.scope = "Protect telecom infrastructure"
        mock_client = MagicMock()

        @asynccontextmanager
        async def mock_connect():
            yield mock_client

        mock_client.connect = mock_connect
        mock_client.get_prompt = AsyncMock(return_value="gathering prompt")

        with pytest.MonkeyPatch().context():
            from unittest.mock import patch

            with patch("src.services.direction.dialogue_service.create_tool_agent") as MockAgent:
                mock_agent = MagicMock()
                mock_agent.run = AsyncMock(
                    return_value=json.dumps(
                        {
                            "question": "Which telecom entities are in scope?",
                            "type": "target_entity",
                            "has_sufficient_context": True,
                            "context": {"target_entities": ["Telenor"]},
                        }
                    )
                )
                MockAgent.return_value = mock_agent
                service = DialogueService(
                    mcp_client=mock_client,
                    ai_orchestrator=MagicMock(),
                )

                # act
                result = await service.generate_clarifying_question(
                    "Investigate telecom risk",
                    ctx,
                    language="en",
                )

        # assert
        assert result.question.question_text == "Which telecom entities are in scope?"
        assert result.question.is_final is False
        assert result.extracted_context == {"target_entities": ["Telenor"]}
        prompt_args = mock_client.get_prompt.await_args.args[1]
        assert "target_entities" in json.loads(prompt_args["missing_fields"])

    @pytest.mark.asyncio
    async def test_generate_summary_passes_context_and_modifications_to_prompt(self):
        # arrange
        ctx = _make_full_context()
        mock_client = MagicMock()

        @asynccontextmanager
        async def mock_connect():
            yield mock_client

        mock_client.connect = mock_connect
        mock_client.get_prompt = AsyncMock(return_value="summary prompt")

        with pytest.MonkeyPatch().context():
            from unittest.mock import patch

            with patch("src.services.direction.dialogue_service.create_tool_agent") as MockAgent:
                mock_agent = MagicMock()
                mock_agent.run = AsyncMock(
                    return_value=json.dumps({"summary": "Norway telecom threat scope."})
                )
                MockAgent.return_value = mock_agent
                service = DialogueService(
                    mcp_client=mock_client,
                    ai_orchestrator=MagicMock(),
                )

                # act
                result = await service.generate_summary(
                    ctx,
                    modifications="Mention emergency communications.",
                    language="en",
                )

        # assert
        assert result == {"summary": "Norway telecom threat scope."}
        prompt_args = mock_client.get_prompt.await_args.args[1]
        assert prompt_args["modifications"] == "Mention emergency communications."
        assert json.loads(prompt_args["perspectives"]) == ["norway"]
