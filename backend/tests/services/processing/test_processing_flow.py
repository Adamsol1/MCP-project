import pytest

from src.models.dialogue import DialogueAction
from src.services.state_machines.processing_flow import ProcessingFlow, ProcessingState

_MOCK_COLLECTED = {
    "session_id": "s1",
    "pir": "Test PIR",
    "attempts": ["raw collected data"],
}
_MOCK_PROCESSED = {
    "session_id": "s1",
    "pir": "Test PIR",
    "attempts": ["raw processed result"],
}


class MockProcessingService:
    def __init__(
        self, *, raise_on_process: bool = False, raise_on_modify: bool = False
    ):
        self.process_calls = []
        self.modify_calls = []
        self.raise_on_process = raise_on_process
        self.raise_on_modify = raise_on_modify

    async def process(self, collected_data, pir):  # noqa: ARG002
        if self.raise_on_process:
            raise RuntimeError("Service unavailable")
        self.process_calls.append({"collected_data": collected_data, "pir": pir})
        return "raw processed result"

    async def modify_processing(self, last_result, user_message):  # noqa: ARG002
        if self.raise_on_modify:
            raise RuntimeError("Service unavailable")
        self.modify_calls.append(
            {"last_result": last_result, "user_message": user_message}
        )
        return "modified processed result"


class MockOrchestrator:
    def __init__(self, *, raise_on_process: bool = False):
        self.generator_model = "mock-model"
        self.attempts = ["attempt-1"]
        self.review_results = [
            {"approved": True, "severity": "none", "suggestions": None}
        ]
        self.retry_explanations = []
        self.raise_on_process = raise_on_process

    async def process_and_review(self, **kwargs):  # noqa: ARG002
        if self.raise_on_process:
            raise RuntimeError("Orchestrator unavailable")
        return "orchestrated processed result"


class MockReviewer:
    pass


# ── initialize ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_initialize_sets_state_to_reviewing(monkeypatch):
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    service = MockProcessingService()
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_collected",
        lambda _: _MOCK_COLLECTED,
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_processed", lambda _: None
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._write_processed", lambda *_: None
    )

    # Act
    response = await flow.initialize(service)

    # Assert
    assert flow.state == ProcessingState.REVIEWING
    assert response.action == DialogueAction.SHOW_PROCESSING


@pytest.mark.asyncio
async def test_initialize_with_orchestrator_sets_pending_reasoning_log(monkeypatch):
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    service = MockProcessingService()
    orchestrator = MockOrchestrator()
    reviewer = MockReviewer()
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_collected",
        lambda _: _MOCK_COLLECTED,
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_processed", lambda _: None
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._write_processed", lambda *_: None
    )

    # Act
    response = await flow.initialize(
        service, orchestrator=orchestrator, reviewer=reviewer
    )

    # Assert
    assert response.action == DialogueAction.SHOW_PROCESSING
    assert flow.pending_reasoning_log is not None
    assert flow.pending_reasoning_log.phase == "processing"
    assert flow.pending_reasoning_log.model_used == "mock-model"


@pytest.mark.asyncio
async def test_initialize_returns_error_when_no_session_id():
    # Arrange
    flow = ProcessingFlow(session_id=None, pir="Test PIR")
    service = MockProcessingService()

    # Act
    response = await flow.initialize(service)

    # Assert
    assert response.action == DialogueAction.ERROR


@pytest.mark.asyncio
async def test_initialize_returns_error_when_no_collected_data(monkeypatch):
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    service = MockProcessingService()
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_collected", lambda _: None
    )

    # Act
    response = await flow.initialize(service)

    # Assert
    assert response.action == DialogueAction.ERROR
    assert flow.state == ProcessingState.PROCESSING  # state must not advance on error


@pytest.mark.asyncio
async def test_initialize_returns_error_when_processing_service_raises(monkeypatch):
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    service = MockProcessingService(raise_on_process=True)
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_collected",
        lambda _: _MOCK_COLLECTED,
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_processed", lambda _: None
    )

    # Act
    response = await flow.initialize(service)

    # Assert
    assert response.action == DialogueAction.ERROR
    assert "Processing failed" in response.content
    assert flow.state == ProcessingState.PROCESSING  # state must not advance on error


@pytest.mark.asyncio
async def test_initialize_error_does_not_leak_exception_details(monkeypatch):
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    service = MockProcessingService(raise_on_process=True)
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_collected",
        lambda _: _MOCK_COLLECTED,
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_processed", lambda _: None
    )

    # Act
    response = await flow.initialize(service)

    # Assert — internal exception message must not reach the frontend
    assert "Service unavailable" not in response.content


@pytest.mark.asyncio
async def test_initialize_returns_error_when_orchestrator_raises(monkeypatch):
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    service = MockProcessingService()
    orchestrator = MockOrchestrator(raise_on_process=True)
    reviewer = MockReviewer()
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_collected",
        lambda _: _MOCK_COLLECTED,
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_processed", lambda _: None
    )

    # Act
    response = await flow.initialize(
        service, orchestrator=orchestrator, reviewer=reviewer
    )

    # Assert
    assert response.action == DialogueAction.ERROR
    assert flow.state == ProcessingState.PROCESSING


# ── process_user_message routing ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_process_user_message_routes_to_handle_reviewing(monkeypatch):
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    flow.state = ProcessingState.REVIEWING
    service = MockProcessingService()
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_processed",
        lambda _: _MOCK_PROCESSED,
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._write_processed", lambda *_: None
    )

    # Act
    response = await flow.process_user_message("modify this", service, approved=False)

    # Assert
    assert response.action == DialogueAction.SHOW_PROCESSING


@pytest.mark.asyncio
async def test_process_user_message_returns_complete_when_not_reviewing():
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    flow.state = ProcessingState.COMPLETE
    service = MockProcessingService()

    # Act
    response = await flow.process_user_message("anything", service)

    # Assert
    assert response.action == DialogueAction.COMPLETE


# ── handle_reviewing ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_reviewing_approve_sets_state_to_complete(monkeypatch):
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    flow.state = ProcessingState.REVIEWING
    service = MockProcessingService()
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_processed",
        lambda _: _MOCK_PROCESSED,
    )

    # Act
    response = await flow.process_user_message("", service, approved=True)

    # Assert
    assert flow.state == ProcessingState.COMPLETE
    assert response.action == DialogueAction.COMPLETE


@pytest.mark.asyncio
async def test_handle_reviewing_modify_stays_in_reviewing(monkeypatch):
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    flow.state = ProcessingState.REVIEWING
    service = MockProcessingService()
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_processed",
        lambda _: _MOCK_PROCESSED,
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._write_processed", lambda *_: None
    )

    # Act
    response = await flow.process_user_message(
        "focus more on malware", service, approved=False
    )

    # Assert
    assert flow.state == ProcessingState.REVIEWING
    assert response.action == DialogueAction.SHOW_PROCESSING
    assert service.modify_calls[0]["user_message"] == "focus more on malware"


@pytest.mark.asyncio
async def test_handle_reviewing_modify_passes_last_attempt_to_service(monkeypatch):
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    flow.state = ProcessingState.REVIEWING
    service = MockProcessingService()
    processed_data = {"session_id": "s1", "pir": "p", "attempts": ["first", "second"]}
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_processed",
        lambda _: processed_data,
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._write_processed", lambda *_: None
    )

    # Act
    await flow.process_user_message("adjust", service, approved=False)

    # Assert — always passes the last attempt, not an earlier one
    assert service.modify_calls[0]["last_result"] == "second"


@pytest.mark.asyncio
async def test_handle_reviewing_modify_returns_error_when_service_raises(monkeypatch):
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    flow.state = ProcessingState.REVIEWING
    service = MockProcessingService(raise_on_modify=True)
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_processed",
        lambda _: _MOCK_PROCESSED,
    )

    # Act
    response = await flow.process_user_message("adjust", service, approved=False)

    # Assert
    assert response.action == DialogueAction.ERROR
    assert "Service unavailable" not in response.content  # no leakage


@pytest.mark.asyncio
async def test_handle_reviewing_modify_handles_empty_processed_data(monkeypatch):
    # Arrange — no prior processed data on disk
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    flow.state = ProcessingState.REVIEWING
    service = MockProcessingService()
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_processed", lambda _: None
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._write_processed", lambda *_: None
    )

    # Act
    response = await flow.process_user_message("adjust", service, approved=False)

    # Assert — falls back to empty string gracefully
    assert response.action == DialogueAction.SHOW_PROCESSING
    assert service.modify_calls[0]["last_result"] == ""


# ── to_dict / from_dict ────────────────────────────────────────────────────────


def test_to_dict_from_dict_roundtrip():
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    flow.state = ProcessingState.REVIEWING

    # Act
    data = flow.to_dict()
    restored = ProcessingFlow.from_dict(data)

    # Assert
    assert restored.session_id == "s1"
    assert restored.pir == "Test PIR"
    assert restored.state == ProcessingState.REVIEWING
    assert restored.pending_reasoning_log is None


def test_to_dict_from_dict_roundtrip_initial_state():
    # Arrange
    flow = ProcessingFlow(session_id="s2", pir="Another PIR")

    # Act
    data = flow.to_dict()
    restored = ProcessingFlow.from_dict(data)

    # Assert
    assert restored.state == ProcessingState.PROCESSING
    assert restored.direction_context is None


# ── default state ─────────────────────────────────────────────────────────────


def test_default_starting_state_is_processing():
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    assert flow.state == ProcessingState.PROCESSING


# ── initialize — additional coverage ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_initialize_response_content_is_raw_result(monkeypatch):
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    service = MockProcessingService()
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_collected",
        lambda _: _MOCK_COLLECTED,
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_processed", lambda _: None
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._write_processed", lambda *_: None
    )

    # Act
    response = await flow.initialize(service)

    # Assert
    assert response.content == "raw processed result"


@pytest.mark.asyncio
async def test_initialize_joins_multiple_attempts_with_separator(monkeypatch):
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    service = MockProcessingService()
    collected_multi = {
        "session_id": "s1",
        "pir": "p",
        "attempts": ["chunk one", "chunk two"],
    }
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_collected",
        lambda _: collected_multi,
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_processed", lambda _: None
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._write_processed", lambda *_: None
    )

    # Act
    await flow.initialize(service)

    # Assert — both chunks joined with the expected separator
    passed = service.process_calls[0]["collected_data"]
    assert "chunk one" in passed
    assert "chunk two" in passed
    assert "\n\n---\n\n" in passed


@pytest.mark.asyncio
async def test_initialize_passes_previous_result_to_orchestrator(monkeypatch):
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    service = MockProcessingService()
    captured_kwargs = {}

    class CapturingOrchestrator(MockOrchestrator):
        async def process_and_review(self, **kwargs):
            captured_kwargs.update(kwargs)
            return "result"

    orchestrator = CapturingOrchestrator()
    reviewer = MockReviewer()
    previous = {"session_id": "s1", "pir": "p", "attempts": ["earlier result"]}
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_collected",
        lambda _: _MOCK_COLLECTED,
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_processed",
        lambda _: previous,
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._write_processed", lambda *_: None
    )

    # Act
    await flow.initialize(service, orchestrator=orchestrator, reviewer=reviewer)

    # Assert — last attempt from previous run is forwarded
    assert captured_kwargs["previous_result"] == "earlier result"


@pytest.mark.asyncio
async def test_initialize_without_orchestrator_leaves_pending_reasoning_log_none(
    monkeypatch,
):
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    service = MockProcessingService()
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_collected",
        lambda _: _MOCK_COLLECTED,
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_processed", lambda _: None
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._write_processed", lambda *_: None
    )

    # Act
    await flow.initialize(service)

    # Assert — no orchestrator means no reasoning log
    assert flow.pending_reasoning_log is None


# ── handle_reviewing approve — additional coverage ────────────────────────────


@pytest.mark.asyncio
async def test_handle_reviewing_approve_writes_reasoning_log(monkeypatch):
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    flow.state = ProcessingState.REVIEWING

    written_logs = []

    class MockResearchLogger:
        def create_log(self, entry):  # noqa: ARG002
            pass

        def write_reasoning_log(self, log):
            written_logs.append(log)

    from src.models.reasoning import ReasoningLog

    flow.research_logger = MockResearchLogger()
    flow.pending_reasoning_log = ReasoningLog(
        session_id="s1",
        phase="processing",
        model_used="mock-model",
        dialogue_turns=[],
        generated_content_attempts=["attempt"],
        review_reasoning=[],
        retry_explanation=[],
        final_approved_content=None,
        timestamps={},
        retry_triggered=False,
        retry_count=0,
    )

    service = MockProcessingService()
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_processed",
        lambda _: _MOCK_PROCESSED,
    )

    # Act
    await flow.process_user_message("", service, approved=True)

    # Assert
    assert len(written_logs) == 1
    assert written_logs[0].final_approved_content is not None


@pytest.mark.asyncio
async def test_handle_reviewing_approve_without_pending_reasoning_log(monkeypatch):
    # Arrange — no pending log, approve should still succeed
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    flow.state = ProcessingState.REVIEWING
    flow.pending_reasoning_log = None
    service = MockProcessingService()
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_processed",
        lambda _: _MOCK_PROCESSED,
    )

    # Act
    response = await flow.process_user_message("", service, approved=True)

    # Assert
    assert response.action == DialogueAction.COMPLETE
    assert flow.state == ProcessingState.COMPLETE


# ── handle_reviewing modify — additional coverage ─────────────────────────────


@pytest.mark.asyncio
async def test_handle_reviewing_modify_response_content_is_modified_result(monkeypatch):
    # Arrange
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    flow.state = ProcessingState.REVIEWING
    service = MockProcessingService()
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._read_processed",
        lambda _: _MOCK_PROCESSED,
    )
    monkeypatch.setattr(
        "src.services.state_machines.processing_flow._write_processed", lambda *_: None
    )

    # Act
    response = await flow.process_user_message("adjust", service, approved=False)

    # Assert — content is what modify_processing returned, not the original
    assert response.content == "modified processed result"


# ── process_user_message — PROCESSING state ───────────────────────────────────


@pytest.mark.asyncio
async def test_process_user_message_returns_complete_when_in_processing_state():
    # Arrange — state is PROCESSING (initialize not yet called)
    flow = ProcessingFlow(session_id="s1", pir="Test PIR")
    assert flow.state == ProcessingState.PROCESSING
    service = MockProcessingService()

    # Act
    response = await flow.process_user_message("anything", service)

    # Assert
    assert response.action == DialogueAction.COMPLETE
