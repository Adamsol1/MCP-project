"""Tests for MCP server initialization."""

import pytest

from src.server import greet, mcp, dialogue_question, generate_pir

VALID_QUESTION_TYPES = ["scope", "timeframe", "target_entities", "actors", "focus", "confirmation"]



class TestServerInitialization:
    """Test that the MCP server initializes correctly."""

    def test_server_has_correct_name(self) -> None:
        """Server should be named ThreatIntelligence."""
        assert mcp.name == "ThreatIntelligence"

    def test_greet_tool_returns_message(self) -> None:
        """Greet tool should return expected message."""
        result = greet.fn()
        assert result == "Hello, this is the MCP Threat Intelligence server!"

    def test_greet_tool_registered(self) -> None:
        """Greet tool should be registered with the server."""
       # print(dir(mcp._tool_manager))
        tools = mcp._tool_manager._tools
        assert "greet" in tools
    def test_dialogue_question_tool(self) -> None:
        #Create mock data"
        user_message = "Investigate APT29"
        missing_fields = ["scope", "timeframe"]
        perspectives = ["neutral"]
        context = {"scope": "", "timeframe": "", "target_entities": []}

        result = dialogue_question.fn(user_message, missing_fields, perspectives, context)

        assert "question" in result
        assert "type" in result
        assert "has_sufficient_context" in result

    def test_dialogue_question_tool_registered(self) -> None:
        """Greet tool should be registered with the server."""
        tools = mcp._tool_manager._tools
        assert "dialogue_question" in tools

    def test_dialogue_question_tool_returns_correct_type_given_question_type_model(self) -> None:

        #Create mock data"
        user_message = "Investigate APT29"
        missing_fields = ["scope", "timeframe"]
        perspectives = ["neutral"]
        context = {"scope": "", "timeframe": "", "target_entities": []}

        result = dialogue_question.fn(user_message, missing_fields, perspectives, context)

        type = result["type"]
        assert  type in VALID_QUESTION_TYPES

    def test_dialogue_question_tool_returns_false_when_missing_fields(self) -> None:
        #Create mock data"
        user_message = "Investigate APT29"
        missing_fields = ["scope", "timeframe"]
        perspectives = ["neutral"]
        context = {"scope": "", "timeframe": "", "target_entities": []}

        result = dialogue_question.fn(user_message, missing_fields, perspectives, context)

        assert not result["has_sufficient_context"]

    def test_dialogue_question_tool_returns_True_when_no_missing_fields(self) -> None:
        #Create mock data"
        user_message = "Investigate APT29"
        missing_fields = []
        perspectives = ["neutral"]
        context = {"scope": "recent campaigns", "timeframe": "last 6 months", "target_entities": ["Norway"]}

        result = dialogue_question.fn(user_message, missing_fields, perspectives, context)

        assert result["has_sufficient_context"]


    def test_dialogue_question_tool_returns_a_question(self) -> None:
        #Create mock data"
        user_message = "Investigate APT29"
        missing_fields = ["scope", "timeframe"]
        perspectives = ["neutral"]
        context = {"scope": "", "timeframe": "", "target_entities": []}

        result = dialogue_question.fn(user_message, missing_fields, perspectives, context)
        assert result["question"]
        #Check if result is string
        assert isinstance(result["question"], str)

    def test_dialogue_question_tool_returns_context(self) -> None:
        #Create mock data
        user_message = "Investigate APT29"
        missing_fields = ["scope", "timeframe"]
        perspectives = ["neutral"]
        context = {"scope": "", "timeframe": "", "target_entities": []}

        result = dialogue_question.fn(user_message, missing_fields, perspectives, context)

        assert "context" in result
        assert result["context"] == context

    def test_dialogue_question_tool_echoes_filled_context(self) -> None:
        #Create mock data with filled context
        user_message = "Investigate APT29"
        missing_fields = []
        perspectives = ["neutral"]
        context = {"scope": "recent campaigns", "timeframe": "last 6 months", "target_entities": ["Norway"]}

        result = dialogue_question.fn(user_message, missing_fields, perspectives, context)

        assert result["context"]["scope"] == "recent campaigns"
        assert result["context"]["timeframe"] == "last 6 months"
        assert result["context"]["target_entities"] == ["Norway"]

    def test_generate_pir_tool_registered(self) -> None:
        """Greet tool should be registered with the server."""
        tools = mcp._tool_manager._tools

        assert "generate_pir" in tools

    def test_generate_pir_tool_returns_correct_value(self) -> None:
        #Create Mock data"
        scope = "identify attack patterns"
        timeframe = "last 6 months"
        target_entities = ["Norway"]
        perspective = ["neutral"]

        result = generate_pir.fn(scope, timeframe, target_entities, perspective)
        print(result)

        assert isinstance(result, str)

    def test_generate_pir_tool_return_is_not_empty(self) -> None:
        #Create Mock data"
        scope = "identify attack patterns"
        timeframe = "last 6 months"
        target_entities = ["Norway"]
        perspective = ["neutral"]

        result = generate_pir.fn(scope, timeframe, target_entities, perspective)

        assert result

    #Context used for testing
    @pytest.mark.parametrize("scope, timeframe, target_entities, perspective", [
    ("", "last 6 months", ["Norway"], "neutral"),
    ("identify attack patterns", "", ["Norway"], "neutral"),
    ("identify attack patterns", "last 6 months", [], "neutral"),
  ])
    def test_generate_pir_tool_raises_value_error_with_insufficient_scope(self, scope, timeframe, target_entities, perspective) -> None:
        with pytest.raises(ValueError):
            generate_pir.fn(scope, timeframe, target_entities, perspective)






