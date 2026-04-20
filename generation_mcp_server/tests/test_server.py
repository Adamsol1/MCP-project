"""Tests for MCP server initialization."""

import json
import pytest

from src.server import greet, mcp, dialogue_question, generate_pir

VALID_QUESTION_TYPES = ["scope", "timeframe", "target_entities", "actors", "focus", "confirmation"]

# Fake AI responses used across multiple tests
_RESPONSE_WITH_MISSING = {
    "question": "What is the scope of your investigation?",
    "type": "scope",
    "has_sufficient_context": False,
    "context": {
        "scope": "",
        "timeframe": "",
        "target_entities": [],
        "threat_actors": ["APT29"],
        "priority_focus": "",
        "perspectives": ["neutral"],
    },
}

_RESPONSE_SUFFICIENT = {
    "question": "Are you ready to proceed?",
    "type": "confirmation",
    "has_sufficient_context": True,
    "context": {
        "scope": "recent campaigns",
        "timeframe": "last 6 months",
        "target_entities": ["Norway"],
        "threat_actors": ["APT29"],
        "priority_focus": "attack vectors",
        "perspectives": ["neutral"],
    },
}



class TestServerInitialization:
    """Test that the MCP server initializes correctly."""

    def test_server_has_correct_name(self) -> None:
        """Server should be named ThreatIntelligence."""
        assert mcp.name == "ThreatIntelligence"

    def test_greet_tool_returns_message(self, mocker) -> None:
        """Greet tool should return expected message."""
        mock_response = mocker.Mock()
        mock_response.text = "Hello!"
        mocker.patch("src.server.client").models.generate_content.return_value = mock_response

        result = greet.fn()

        assert "Hello, this is the MCP Threat Intelligence server!" in result

    def test_greet_tool_registered(self) -> None:
        """Greet tool should be registered with the server."""
       # print(dir(mcp._tool_manager))
        tools = mcp._tool_manager._tools
        assert "greet" in tools
    def test_dialogue_question_tool(self, mocker) -> None:
        mock_response = mocker.Mock()
        mock_response.text = json.dumps(_RESPONSE_WITH_MISSING)
        mocker.patch("src.server.client").models.generate_content.return_value = mock_response

        result = dialogue_question.fn("Investigate APT29", ["scope", "timeframe"], ["neutral"], {})

        assert "question" in result
        assert "type" in result
        assert "has_sufficient_context" in result

    def test_dialogue_question_tool_registered(self) -> None:
        """Greet tool should be registered with the server."""
        tools = mcp._tool_manager._tools
        assert "dialogue_question" in tools

    def test_dialogue_question_tool_returns_correct_type_given_question_type_model(self, mocker) -> None:
        mock_response = mocker.Mock()
        mock_response.text = json.dumps(_RESPONSE_WITH_MISSING)
        mocker.patch("src.server.client").models.generate_content.return_value = mock_response

        result = dialogue_question.fn("Investigate APT29", ["scope", "timeframe"], ["neutral"], {})

        assert result["type"] in VALID_QUESTION_TYPES

    def test_dialogue_question_tool_returns_false_when_missing_fields(self, mocker) -> None:
        # Even if AI somehow returns True, backend overrides to False when missing_fields present
        mock_response = mocker.Mock()
        mock_response.text = json.dumps({**_RESPONSE_WITH_MISSING, "has_sufficient_context": True})
        mocker.patch("src.server.client").models.generate_content.return_value = mock_response

        result = dialogue_question.fn("Investigate APT29", ["scope", "timeframe"], ["neutral"], {})

        assert not result["has_sufficient_context"]

    def test_dialogue_question_tool_returns_True_when_no_missing_fields(self, mocker) -> None:
        mock_response = mocker.Mock()
        mock_response.text = json.dumps(_RESPONSE_SUFFICIENT)
        mocker.patch("src.server.client").models.generate_content.return_value = mock_response

        result = dialogue_question.fn("Investigate APT29", [], ["neutral"], {
            "scope": "recent campaigns", "timeframe": "last 6 months", "target_entities": ["Norway"]
        })

        assert result["has_sufficient_context"]


    def test_dialogue_question_tool_returns_a_question(self, mocker) -> None:
        mock_response = mocker.Mock()
        mock_response.text = json.dumps(_RESPONSE_WITH_MISSING)
        mocker.patch("src.server.client").models.generate_content.return_value = mock_response

        result = dialogue_question.fn("Investigate APT29", ["scope", "timeframe"], ["neutral"], {})

        assert result["question"]
        assert isinstance(result["question"], str)

    def test_dialogue_question_tool_returns_context(self, mocker) -> None:
        mock_response = mocker.Mock()
        mock_response.text = json.dumps(_RESPONSE_WITH_MISSING)
        mocker.patch("src.server.client").models.generate_content.return_value = mock_response

        result = dialogue_question.fn("Investigate APT29", ["scope", "timeframe"], ["neutral"], {})

        assert "context" in result
        assert isinstance(result["context"], dict)

    def test_dialogue_question_tool_echoes_filled_context(self, mocker) -> None:
        mock_response = mocker.Mock()
        mock_response.text = json.dumps(_RESPONSE_SUFFICIENT)
        mocker.patch("src.server.client").models.generate_content.return_value = mock_response

        result = dialogue_question.fn("Investigate APT29", [], ["neutral"], {
            "scope": "recent campaigns", "timeframe": "last 6 months", "target_entities": ["Norway"]
        })

        assert result["context"]["scope"] == "recent campaigns"
        assert result["context"]["timeframe"] == "last 6 months"
        assert result["context"]["target_entities"] == ["Norway"]

    def test_dialogue_question_defaults_to_neutral_when_perspectives_empty(self, mocker) -> None:
        mock_response = mocker.Mock()
        mock_response.text = json.dumps(_RESPONSE_WITH_MISSING)
        mock_client = mocker.patch("src.server.client")
        mock_client.models.generate_content.return_value = mock_response

        dialogue_question.fn("Investigate APT29", ["scope"], [], {})

        # Verify "neutral" was injected into the prompt sent to Gemini
        call_args = mock_client.models.generate_content.call_args
        assert "neutral" in call_args.kwargs["contents"]

    def test_dialogue_question_context_has_all_required_subkeys(self, mocker) -> None:
        mock_response = mocker.Mock()
        mock_response.text = json.dumps(_RESPONSE_SUFFICIENT)
        mocker.patch("src.server.client").models.generate_content.return_value = mock_response

        result = dialogue_question.fn("Investigate APT29", [], ["neutral"], {})

        required_keys = ["scope", "timeframe", "target_entities", "threat_actors", "priority_focus", "perspectives"]
        for key in required_keys:
            assert key in result["context"], f"Missing key in context: {key}"

    def test_generate_pir_tool_registered(self) -> None:
        """Greet tool should be registered with the server."""
        tools = mcp._tool_manager._tools

        assert "generate_pir" in tools

    def test_generate_pir_tool_returns_correct_value(self, mocker) -> None:
        fake_pir = json.dumps({"result": "PIR summary", "pirs": [], "reasoning": "test"})
        mock_response = mocker.Mock()
        mock_response.text = fake_pir
        mocker.patch("src.server.client").models.generate_content.return_value = mock_response

        result = generate_pir.fn("identify attack patterns", "last 6 months", ["Norway"], ["neutral"],
                                 threat_actors=["APT29"], priority_focus="attack vectors")

        assert isinstance(result, str)

    def test_generate_pir_tool_return_is_not_empty(self, mocker) -> None:
        fake_pir = json.dumps({"result": "PIR summary", "pirs": [], "reasoning": "test"})
        mock_response = mocker.Mock()
        mock_response.text = fake_pir
        mocker.patch("src.server.client").models.generate_content.return_value = mock_response

        result = generate_pir.fn("identify attack patterns", "last 6 months", ["Norway"], ["neutral"],
                                 threat_actors=["APT29"], priority_focus="attack vectors")

        assert result

    #Context used for testing
    @pytest.mark.parametrize("scope, timeframe, target_entities, perspective", [
    ("", "last 6 months", ["Norway"], "neutral"),
    ("identify attack patterns", "", ["Norway"], "neutral"),
    ("identify attack patterns", "last 6 months", [], "neutral"),
  ])
    def test_generate_pir_tool_raises_value_error_with_insufficient_scope(self, scope, timeframe, target_entities, perspective) -> None:
        with pytest.raises(ValueError):
            generate_pir.fn(scope, timeframe, target_entities, perspective, threat_actors=["APT29"], priority_focus="attack vectors")






