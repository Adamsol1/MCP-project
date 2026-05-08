import json

import pytest

from src.models.dialogue import ClarifyingQuestion, DialogueContext, QuestionResult
from src.services.direction import dialogue_service as dialogue_service_module
from src.services.direction.dialogue_service import DialogueService


class MockMCPClient:
    def __init__(self):
        self.calls = []

    def connect(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):  # noqa: ARG002
        return False

    async def get_prompt(self, prompt_name, params):
        self.calls.append({"prompt_name": prompt_name, "params": params})

        if prompt_name != "direction_gathering":
            return "{}"

        missing_fields = json.loads(params["missing_fields"])
        if "scope" in missing_fields:
            return json.dumps(
                {
                    "question": "What is the scope of your investigation?",
                    "type": "scope",
                    "has_sufficient_context": True,
                    "context": {},
                }
            )
        if "timeframe" in missing_fields:
            return json.dumps(
                {
                    "question": "What time period are you interested in?",
                    "type": "timeframe",
                    "has_sufficient_context": True,
                    "context": {},
                }
            )
        if "threat_actors" in missing_fields:
            return json.dumps(
                {
                    "question": "Which threat actors are relevant to your investigation?",
                    "type": "actors",
                    "has_sufficient_context": False,
                    "context": {},
                }
            )

        return json.dumps(
            {
                "question": "I have enough information to proceed.",
                "type": "confirmation",
                "has_sufficient_context": True,
                "context": {},
            }
        )


class MockToolCallingAgent:
    def __init__(self, mcp_client):  # noqa: ARG002
        pass

    async def run(self, system_prompt: str, task: str, **kwargs):  # noqa: ARG002
        return system_prompt


class MockAIOrchestrator:
    pass


def _build_service(monkeypatch):
    monkeypatch.setattr(
        dialogue_service_module,
        "create_tool_agent",
        lambda mcp_client: MockToolCallingAgent(mcp_client),
    )
    mcp_client = MockMCPClient()
    return DialogueService(mcp_client, MockAIOrchestrator()), mcp_client


def test_parse_json_handles_trailing_text_after_json():
    parsed = DialogueService._parse_json('Here is the PIR JSON:\n{"pirs": []}\nDone.')

    assert parsed == {"pirs": []}


def test_parse_json_repairs_trailing_commas_in_balanced_object():
    parsed = DialogueService._parse_json(
        'Result:\n{"pir_text": "x", "pirs": [], "claims": [], "sources": [],}'
    )

    assert parsed["pir_text"] == "x"
    assert parsed["pirs"] == []


def test_parse_json_prefers_full_pir_over_nested_claim_object():
    parsed = DialogueService._parse_json(
        """
        {"id": "claim_1", "text": "nested claim", "source_ref": "[1]", "source_id": "s1"}
        {
          "pir_text": "full response",
          "claims": [],
          "sources": [],
          "pirs": [{"question": "q", "priority": "high", "rationale": "r", "source_ids": []}],
          "reasoning": "because"
        }
        """
    )

    assert parsed["pir_text"] == "full response"
    assert parsed["pirs"][0]["question"] == "q"


def test_parse_json_handles_bare_pir_array_after_preamble():
    parsed = DialogueService._parse_json(
        """
        Here are the PIRs:
        [
          {"question": "Which actors are targeting Storebrand?", "priority": "high"}
        ]
        """
    )

    assert parsed[0]["question"] == "Which actors are targeting Storebrand?"


def test_normalize_pir_accepts_compact_pirs_only_shape():
    parsed = DialogueService._normalize_response_shape(
        {"pirs": [{"question": "What changed?", "priority": "urgent"}]},
        "PIR",
    )

    assert parsed["pir_text"] == ""
    assert parsed["claims"] == []
    assert parsed["sources"] == []
    assert parsed["pirs"][0]["priority"] == "medium"


def test_normalize_pir_accepts_local_model_wrapper_alias():
    parsed = DialogueService._normalize_response_shape(
        {
            "priority_intelligence_requirements": [
                {
                    "requirement": "What is the most likely espionage vector?",
                    "priority": "high",
                    "reason": "Decision support",
                }
            ],
            "summary": "Compact local-model PIR response",
        },
        "PIR",
    )

    assert parsed["pir_text"] == "Compact local-model PIR response"
    assert parsed["pirs"][0]["question"] == "What is the most likely espionage vector?"
    assert parsed["pirs"][0]["rationale"] == "Decision support"


def test_normalize_pir_accepts_bare_question_list():
    parsed = DialogueService._normalize_response_shape(
        ["Which threat actors are most relevant?"],
        "PIR",
    )

    assert parsed["pirs"] == [
        {
            "question": "Which threat actors are most relevant?",
            "priority": "medium",
            "rationale": "",
            "source_ids": [],
        }
    ]


def _patch_repair_provider(monkeypatch, repair_text: str) -> None:
    class FakeProvider:
        async def generate_json_text(self, prompt: str):  # noqa: ARG002
            return repair_text

    monkeypatch.setattr(dialogue_service_module, "get_provider", lambda: FakeProvider())


@pytest.mark.asyncio
async def test_parse_or_repair_json_rejects_claim_object_for_pir(monkeypatch):
    _patch_repair_provider(
        monkeypatch,
        json.dumps(
            {
                "pir_text": "repaired",
                "claims": [],
                "sources": [],
                "pirs": [
                    {
                        "question": "What is the espionage risk?",
                        "priority": "high",
                        "rationale": "Decision support",
                        "source_ids": [],
                    }
                ],
                "reasoning": "The original output was only a nested claim.",
            }
        ),
    )
    service = DialogueService(MockMCPClient(), MockAIOrchestrator())

    result = await service._parse_or_repair_json(
        raw='{"id": "claim_1", "text": "not a full PIR"}',
        repair_prompt="repair this",
        label="PIR",
    )

    assert result["pir_text"] == "repaired"
    assert result["pirs"][0]["priority"] == "high"


@pytest.mark.asyncio
async def test_parse_or_repair_json_accepts_pirs_only_for_pir():
    service = DialogueService(MockMCPClient(), MockAIOrchestrator())

    result = await service._parse_or_repair_json(
        raw='{"pirs": [{"question": "What is the risk?", "priority": "high"}]}',
        repair_prompt="repair this",
        label="PIR",
    )

    assert result["claims"] == []
    assert result["sources"] == []
    assert result["pirs"][0]["question"] == "What is the risk?"


@pytest.mark.asyncio
async def test_parse_or_repair_json_accepts_alias_wrapper_for_pir():
    service = DialogueService(MockMCPClient(), MockAIOrchestrator())

    result = await service._parse_or_repair_json(
        raw=json.dumps(
            {
                "priority_intelligence_requirements": [
                    {
                        "requirement": "Which TTPs are likely?",
                        "priority": "high",
                    }
                ]
            }
        ),
        repair_prompt="repair this",
        label="PIR",
    )

    assert result["pirs"][0]["question"] == "Which TTPs are likely?"


@pytest.mark.asyncio
async def test_parse_or_repair_json_repairs_with_model(monkeypatch):
    _patch_repair_provider(
        monkeypatch,
        '{"question": "What scope?", "type": "scope", "has_sufficient_context": false, "context": {}}',
    )

    service = DialogueService(MockMCPClient(), MockAIOrchestrator())
    result = await service._parse_or_repair_json(
        raw="What scope?",
        repair_prompt="repair this",
        label="clarifying question",
    )

    assert result["question"] == "What scope?"
    assert result["type"] == "scope"


@pytest.mark.asyncio
async def test_parse_or_repair_json_raises_when_repair_is_unparseable(monkeypatch):
    _patch_repair_provider(monkeypatch, "still not json")

    service = DialogueService(MockMCPClient(), MockAIOrchestrator())

    with pytest.raises(ValueError, match="after repair"):
        await service._parse_or_repair_json(
            raw="not json",
            repair_prompt="repair this",
            label="PIR",
        )


@pytest.mark.asyncio
async def test_generate_clarifying_question_returns_clarifying_question(monkeypatch):
    service, mcp_client = _build_service(monkeypatch)

    context = DialogueContext()
    context.initial_query = "Investigate APT29"

    result = await service.generate_clarifying_question(
        user_message="Investigate APT29", context=context
    )

    assert isinstance(result, QuestionResult)
    assert isinstance(result.question, ClarifyingQuestion)
    assert result.question.question_text != ""
    assert result.question.question_type != ""
    assert isinstance(result.extracted_context, dict)
    assert mcp_client.calls[0]["params"]["language"] == "en"


@pytest.mark.asyncio
async def test_generate_clarifying_question_asks_about_scope_when_missing(monkeypatch):
    service, mcp_client = _build_service(monkeypatch)

    context = DialogueContext()
    context.initial_query = "Investigate APT29"

    result = await service.generate_clarifying_question(
        user_message="Investigate APT29", context=context
    )

    assert result.question.question_type == "scope"
    assert result.question.is_final is False
    assert "scope" in json.loads(mcp_client.calls[0]["params"]["missing_fields"])
    assert mcp_client.calls[0]["params"]["language"] == "en"


@pytest.mark.asyncio
async def test_generate_clarifying_question_asks_about_timeframe_when_scope_set(
    monkeypatch,
):
    service, mcp_client = _build_service(monkeypatch)

    context = DialogueContext()
    context.initial_query = "Investigate APT29"
    context.scope = "recent campaigns"

    result = await service.generate_clarifying_question(
        user_message="Focus on recent campaigns", context=context
    )

    assert result.question.question_type == "timeframe"
    assert result.question.is_final is False
    assert "timeframe" in json.loads(mcp_client.calls[0]["params"]["missing_fields"])


@pytest.mark.asyncio
async def test_generate_clarifying_question_asks_about_actors_when_remaining(
    monkeypatch,
):
    service, mcp_client = _build_service(monkeypatch)

    context = DialogueContext()
    context.initial_query = "Investigate APT29"
    context.scope = "recent campaigns"
    context.timeframe = "last 6 months"
    context.target_entities = ["Nordic countries"]

    result = await service.generate_clarifying_question(
        user_message="Focus on known actors", context=context
    )

    assert result.question.question_type == "actors"
    assert result.question.is_final is False
    assert "threat_actors" in json.loads(
        mcp_client.calls[0]["params"]["missing_fields"]
    )


@pytest.mark.asyncio
async def test_generate_clarifying_question_is_final_when_context_complete(monkeypatch):
    service, mcp_client = _build_service(monkeypatch)

    context = DialogueContext()
    context.initial_query = "Investigate APT29"
    context.scope = "recent campaigns"
    context.timeframe = "last 6 months"
    context.target_entities = ["Nordic countries"]
    context.threat_actors = ["APT29"]
    context.priority_focus = "TTPs"

    result = await service.generate_clarifying_question(
        user_message="Nordic countries", context=context
    )

    assert result.question.is_final is True
    assert json.loads(mcp_client.calls[0]["params"]["missing_fields"]) == []
