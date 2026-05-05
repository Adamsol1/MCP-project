import json

import pytest

from src.models.dialogue import DialogueAction
from src.services.collection.collection_service import CollectionService
from src.services.state_machines.collection_flow import CollectionFlow, CollectionState


def async_return(value):
    async def _inner(*_args, **_kwargs):
        return value

    return _inner


class MockCollectionService:
    def __init__(self):
        self.plan = "Mock collection plan"
        self.collected = '{"collected_data": [], "source_summary": []}'
        self.modified = '{"collected_data": [], "source_summary": []}'

    async def generate_collection_plan(
        self, _pir, _feedback=None, current_plan=None, language="en"
    ):  # noqa: ARG002
        return self.plan

    async def collect(self, sources, pir, plan, **kwargs):  # noqa: ARG002
        return self.collected

    async def modify_summary(self, _raw, _user_message, language="en"):  # noqa: ARG002
        return self.modified

    @staticmethod
    def parse_collected_data(raw_data):  # noqa: ARG004
        return {"collected_data": [], "source_summary": []}


class MockOrchestrator:
    def __init__(self):
        self.generator_model = "mock-model"
        self.attempts = ["attempt-1"]
        self.review_results = [
            {"approved": True, "severity": "none", "suggestions": None}
        ]
        self.retry_explanations = []

    async def collect_and_review(self, **kwargs):  # noqa: ARG002
        return '{"collected_data": [], "source_summary": []}'


# --- initialize ---


@pytest.mark.asyncio
async def test_initialize_sets_state_to_plan_confirming():
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    service = MockCollectionService()

    # Act
    response = await flow.initialize(service)

    # Assert
    assert flow.state == CollectionState.PLAN_CONFIRMING
    assert response.action == DialogueAction.SHOW_PLAN
    assert flow.collection_plan == "Mock collection plan"


# --- handle_plan_confirming ---


@pytest.mark.asyncio
async def test_plan_confirming_approve_transitions_to_collecting():
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.PLAN_CONFIRMING
    service = MockCollectionService()

    # Act
    response = await flow.handle_plan_confirming(
        user_message="",
        collection_service=service,
        approved=True,
        selected_sources=["OTX", "MISP"],
    )

    # Assert
    assert flow.state == CollectionState.COLLECTING
    assert response.action == DialogueAction.START_COLLECTING
    assert flow.selected_sources == ["OTX", "MISP"]


@pytest.mark.asyncio
async def test_plan_confirming_approve_without_sources_stores_empty_list():
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.PLAN_CONFIRMING
    service = MockCollectionService()

    # Act
    await flow.handle_plan_confirming(
        user_message="",
        collection_service=service,
        approved=True,
        selected_sources=None,
    )

    # Assert
    assert flow.selected_sources == []


@pytest.mark.asyncio
async def test_plan_confirming_reject_stays_in_plan_confirming():
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.PLAN_CONFIRMING
    service = MockCollectionService()

    # Act
    response = await flow.handle_plan_confirming(
        user_message="Make it shorter",
        collection_service=service,
        approved=False,
        selected_sources=None,
    )

    # Assert
    assert flow.state == CollectionState.PLAN_CONFIRMING
    assert response.action == DialogueAction.SHOW_PLAN


# --- handle_collecting ---


@pytest.mark.asyncio
async def test_handle_collecting_without_orchestrator_uses_service(monkeypatch):
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.COLLECTING
    flow.collection_plan = "Plan"
    service = MockCollectionService()
    monkeypatch.setattr(
        "src.services.state_machines.collection_flow._write_collected",
        async_return(None),
    )

    # Act
    response = await flow.handle_collecting(collection_service=service)

    # Assert
    assert flow.state == CollectionState.REVIEWING
    assert response.action == DialogueAction.SHOW_COLLECTION


@pytest.mark.asyncio
async def test_handle_collecting_with_orchestrator_uses_orchestrator(monkeypatch):
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.COLLECTING
    flow.collection_plan = "Plan"
    service = MockCollectionService()
    orchestrator = MockOrchestrator()
    monkeypatch.setattr(
        "src.services.state_machines.collection_flow._write_collected",
        async_return(None),
    )

    # Act
    response = await flow.handle_collecting(
        collection_service=service, orchestrator=orchestrator, reviewer=object()
    )

    # Assert
    assert flow.state == CollectionState.REVIEWING
    assert response.action == DialogueAction.SHOW_COLLECTION


@pytest.mark.asyncio
async def test_handle_collecting_exception_resets_to_plan_confirming(monkeypatch):
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.COLLECTING

    class FailingService:
        async def collect(self, *_args, **_kwargs):
            raise RuntimeError("Network error")

        @staticmethod
        def parse_collected_data(raw):  # noqa: ARG004
            return {}

    # Act
    response = await flow.handle_collecting(collection_service=FailingService())

    # Assert
    assert flow.state == CollectionState.PLAN_CONFIRMING
    assert response.action == DialogueAction.ERROR


@pytest.mark.asyncio
async def test_handle_collecting_consumes_gather_more_feedback(monkeypatch):
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.COLLECTING
    flow.collection_plan = "Plan"
    flow.gather_more_feedback = "Focus on TTPs"
    service = MockCollectionService()
    monkeypatch.setattr(
        "src.services.state_machines.collection_flow._write_collected",
        async_return(None),
    )

    # Act
    await flow.handle_collecting(collection_service=service)

    # Assert
    assert flow.gather_more_feedback is None


# --- handle_reviewing ---


@pytest.mark.asyncio
async def test_handle_reviewing_approve_transitions_to_complete(monkeypatch):
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.REVIEWING
    service = MockCollectionService()
    monkeypatch.setattr(
        "src.services.state_machines.collection_flow._read_collected",
        async_return(None),
    )

    # Act
    response = await flow.handle_reviewing(
        user_message="", collection_service=service, approved=True, gather_more=False
    )

    # Assert
    assert flow.state == CollectionState.COMPLETE
    assert response.action == DialogueAction.COMPLETE


@pytest.mark.asyncio
async def test_handle_reviewing_gather_more_transitions_to_collecting():
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.REVIEWING
    flow.selected_sources = ["OTX"]
    service = MockCollectionService()

    # Act
    response = await flow.handle_reviewing(
        user_message="Look for more recent data",
        collection_service=service,
        approved=False,
        gather_more=True,
        selected_sources=["OTX", "MISP"],
    )

    # Assert
    assert flow.state == CollectionState.COLLECTING
    assert response.action == DialogueAction.START_COLLECTING
    assert flow.selected_sources == ["OTX", "MISP"]


@pytest.mark.asyncio
async def test_handle_reviewing_gather_more_keeps_existing_sources_when_none():
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.REVIEWING
    flow.selected_sources = ["OTX"]
    service = MockCollectionService()

    # Act
    await flow.handle_reviewing(
        user_message="",
        collection_service=service,
        approved=False,
        gather_more=True,
        selected_sources=None,
    )

    # Assert
    assert flow.selected_sources == ["OTX"]


@pytest.mark.asyncio
async def test_handle_reviewing_modify_returns_show_collection(monkeypatch):
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.REVIEWING
    service = MockCollectionService()
    monkeypatch.setattr(
        "src.services.state_machines.collection_flow._read_collected",
        async_return({"attempts": ["raw data"]}),
    )
    monkeypatch.setattr(
        "src.services.state_machines.collection_flow._write_collected",
        async_return(None),
    )

    # Act
    response = await flow.handle_reviewing(
        user_message="Remove irrelevant data",
        collection_service=service,
        approved=False,
        gather_more=False,
    )

    # Assert
    assert flow.state == CollectionState.REVIEWING
    assert response.action == DialogueAction.SHOW_COLLECTION


# --- collected data handling ---


@pytest.mark.asyncio
async def test_handle_collecting_response_contains_parsed_data(monkeypatch):
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.COLLECTING
    flow.collection_plan = "Plan"
    service = MockCollectionService()
    parsed = {
        "collected_data": [{"source": "OTX", "content": "APT29 data"}],
        "source_summary": [],
    }
    monkeypatch.setattr(CollectionService, "parse_collected_data", lambda raw: parsed)  # noqa: ARG005
    monkeypatch.setattr(
        "src.services.state_machines.collection_flow._write_collected",
        async_return(None),
    )

    # Act
    response = await flow.handle_collecting(collection_service=service)

    # Assert
    assert response.action == DialogueAction.SHOW_COLLECTION
    payload = json.loads(response.content)
    assert payload["collected_data"][0]["source"] == "OTX"


@pytest.mark.asyncio
async def test_handle_reviewing_gather_more_sets_feedback_from_user_message():
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.REVIEWING
    service = MockCollectionService()

    # Act
    await flow.handle_reviewing(
        user_message="Focus on recent TTPs",
        collection_service=service,
        approved=False,
        gather_more=True,
    )

    # Assert
    assert flow.gather_more_feedback == "Focus on recent TTPs"


# --- process_user_message routing ---


@pytest.mark.asyncio
async def test_process_user_message_routes_to_plan_confirming(monkeypatch):
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.PLAN_CONFIRMING
    service = MockCollectionService()

    # Act
    response = await flow.process_user_message(
        user_message="", collection_service=service, approved=True
    )

    # Assert
    assert response.action == DialogueAction.START_COLLECTING


@pytest.mark.asyncio
async def test_process_user_message_routes_to_collecting(monkeypatch):
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.COLLECTING
    flow.collection_plan = "Plan"
    service = MockCollectionService()
    monkeypatch.setattr(
        "src.services.state_machines.collection_flow._write_collected",
        async_return(None),
    )

    # Act
    response = await flow.process_user_message(
        user_message="", collection_service=service
    )

    # Assert
    assert flow.state == CollectionState.REVIEWING
    assert response.action == DialogueAction.SHOW_COLLECTION


@pytest.mark.asyncio
async def test_process_user_message_routes_to_reviewing(monkeypatch):
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.REVIEWING
    service = MockCollectionService()
    monkeypatch.setattr(
        "src.services.state_machines.collection_flow._read_collected",
        async_return(None),
    )

    # Act
    response = await flow.process_user_message(
        user_message="", collection_service=service, approved=True
    )

    # Assert
    assert flow.state == CollectionState.COMPLETE
    assert response.action == DialogueAction.COMPLETE


@pytest.mark.asyncio
async def test_process_user_message_returns_complete_for_unknown_state():
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.COMPLETE
    service = MockCollectionService()

    # Act
    response = await flow.process_user_message(
        user_message="", collection_service=service
    )

    # Assert
    assert response.action == DialogueAction.COMPLETE


# --- failure cases ---


@pytest.mark.asyncio
async def test_initialize_returns_error_when_plan_generation_fails():
    # Arrange
    class FailingService(MockCollectionService):
        async def generate_collection_plan(
            self, _pir, _feedback=None, current_plan=None, language="en"
        ):
            raise RuntimeError("LLM unavailable")

    flow = CollectionFlow(session_id="s1", pir="Test PIR")

    # Act
    response = await flow.initialize(FailingService())

    # Assert
    assert response.action == DialogueAction.ERROR
    assert flow.state == CollectionState.PLANNING


@pytest.mark.asyncio
async def test_handle_reviewing_modify_returns_error_when_modify_summary_fails(
    monkeypatch,
):
    # Arrange
    class FailingService(MockCollectionService):
        async def modify_summary(self, _raw, _user_message, language="en"):
            raise RuntimeError("LLM unavailable")

    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.REVIEWING
    monkeypatch.setattr(
        "src.services.state_machines.collection_flow._read_collected",
        async_return({"attempts": ["raw data"]}),
    )

    # Act
    response = await flow.handle_reviewing(
        user_message="Remove irrelevant data",
        collection_service=FailingService(),
        approved=False,
        gather_more=False,
    )

    # Assert
    assert response.action == DialogueAction.ERROR
    assert flow.state == CollectionState.REVIEWING


# --- initial state ---


def test_initial_state_is_planning():
    # Arrange / Act
    flow = CollectionFlow(session_id="s1", pir="Test PIR")

    # Assert
    assert flow.state == CollectionState.PLANNING


# --- approved=None treated as reject ---


@pytest.mark.asyncio
async def test_plan_confirming_approved_none_treated_as_reject():
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.PLAN_CONFIRMING
    service = MockCollectionService()

    # Act
    response = await flow.handle_plan_confirming(
        user_message="",
        collection_service=service,
        approved=None,
        selected_sources=None,
    )

    # Assert
    assert flow.state == CollectionState.PLAN_CONFIRMING
    assert response.action == DialogueAction.SHOW_PLAN


# --- activity_summary added when orchestrator has review results ---


@pytest.mark.asyncio
async def test_handle_collecting_adds_activity_summary_when_orchestrator_has_reviews(
    monkeypatch,
):
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.COLLECTING
    flow.collection_plan = "Plan"
    flow.selected_sources = ["OTX"]
    service = MockCollectionService()
    orchestrator = MockOrchestrator()
    monkeypatch.setattr(
        "src.services.state_machines.collection_flow._write_collected",
        async_return(None),
    )

    # Act
    response = await flow.handle_collecting(
        collection_service=service, orchestrator=orchestrator, reviewer=object()
    )

    # Assert
    assert response.review_activity
    assert response.review_activity[0].reviewer_approved is True
    assert response.review_activity[0].sources_used == ["OTX"]


# --- gather_more_feedback passed to orchestrator ---


@pytest.mark.asyncio
async def test_handle_collecting_passes_gather_more_feedback_to_orchestrator(
    monkeypatch,
):
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.COLLECTING
    flow.collection_plan = "Plan"
    flow.gather_more_feedback = "Focus on TTPs"
    received_feedback = {}

    class CapturingOrchestrator(MockOrchestrator):
        async def collect_and_review(self, **kwargs):
            received_feedback["feedback"] = kwargs.get("feedback")
            return '{"collected_data": [], "source_summary": []}'

    monkeypatch.setattr(
        "src.services.state_machines.collection_flow._write_collected",
        async_return(None),
    )
    service = MockCollectionService()

    # Act
    await flow.handle_collecting(
        collection_service=service,
        orchestrator=CapturingOrchestrator(),
        reviewer=object(),
    )

    # Assert
    assert received_feedback["feedback"] == "Focus on TTPs"


# --- handle_reviewing modify with empty collected data ---


@pytest.mark.asyncio
async def test_handle_reviewing_modify_with_empty_collected_data(monkeypatch):
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    flow.state = CollectionState.REVIEWING
    service = MockCollectionService()
    monkeypatch.setattr(
        "src.services.state_machines.collection_flow._read_collected",
        async_return(None),
    )
    monkeypatch.setattr(
        "src.services.state_machines.collection_flow._write_collected",
        async_return(None),
    )

    # Act
    response = await flow.handle_reviewing(
        user_message="Remove irrelevant data",
        collection_service=service,
        approved=False,
        gather_more=False,
    )

    # Assert
    assert response.action == DialogueAction.SHOW_COLLECTION


# --- full flow integration ---


@pytest.mark.asyncio
async def test_full_flow_planning_to_complete(monkeypatch):
    # Arrange
    flow = CollectionFlow(session_id="s1", pir="Test PIR")
    service = MockCollectionService()
    monkeypatch.setattr(
        "src.services.state_machines.collection_flow._write_collected",
        async_return(None),
    )
    monkeypatch.setattr(
        "src.services.state_machines.collection_flow._read_collected",
        async_return(None),
    )

    # Act — initialize
    response = await flow.initialize(service)
    assert flow.state == CollectionState.PLAN_CONFIRMING
    assert response.action == DialogueAction.SHOW_PLAN

    # Act — approve plan
    response = await flow.process_user_message(
        user_message="",
        collection_service=service,
        approved=True,
        selected_sources=["OTX"],
    )
    assert flow.state == CollectionState.COLLECTING
    assert response.action == DialogueAction.START_COLLECTING

    # Act — collect
    response = await flow.process_user_message(
        user_message="",
        collection_service=service,
    )
    assert flow.state == CollectionState.REVIEWING
    assert response.action == DialogueAction.SHOW_COLLECTION

    # Act — approve collection
    response = await flow.process_user_message(
        user_message="",
        collection_service=service,
        approved=True,
    )
    assert flow.state == CollectionState.COMPLETE
    assert response.action == DialogueAction.COMPLETE
