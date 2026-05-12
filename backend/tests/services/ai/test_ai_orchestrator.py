# Tests for AI Orchestrator - coordinates AI #1 (generate) and AI #2 (review)

import pytest

from src.models.analysis import AnalysisDraft, FindingModel, ProcessingResult
from src.models.dialogue import DialogueContext
from src.services.ai.ai_orchestrator import AIOrchestrator
from tests.services.conftest import (
    MockGenerator,
    MockLogger,
    MockReviewer,
    make_approved_result,
    make_rejected_result,
)


@pytest.mark.asyncio
async def test_orchestrator_approves_on_first_try():
    context = DialogueContext()
    context.scope = "identify attack patterns"
    context.timeframe = "last 6 months"
    context.target_entities = ["Norway"]

    generator = MockGenerator()
    reviewer = MockReviewer(responses=[make_approved_result()])
    logger = MockLogger()
    orchestrator = AIOrchestrator(
        research_logger=logger,
        generator_model="test-model",
    )

    result = await orchestrator.generate_and_review_pir(
        context,
        generator,
        reviewer,
        phase="direction",
        session_id="test-session-id",
    )

    assert result == "Generated PIR based on context"
    assert reviewer.call_count == 1
    assert len(orchestrator.attempts) == 1
    assert len(orchestrator.review_results) == 1
    assert len(logger.logs) == 1
    assert logger.logs[0].session_id == "test-session-id"
    assert logger.logs[0].model_used == "test-model"


@pytest.mark.asyncio
async def test_orchestrator_retries_and_succeeds():
    """A major rejection triggers one retry and returns the accepted retry result."""
    context = DialogueContext()
    context.scope = "identify attack patterns"
    context.timeframe = "last 6 months"
    context.target_entities = ["Norway"]

    generator = MockGenerator()
    reviewer = MockReviewer(responses=[make_rejected_result(), make_approved_result()])
    logger = MockLogger()
    orchestrator = AIOrchestrator(
        research_logger=logger,
        generator_model="test-model",
    )

    result = await orchestrator.generate_and_review_pir(
        context,
        generator,
        reviewer,
        phase="direction",
        session_id="test-session-id",
    )

    assert result == "Generated PIR based on context"
    assert reviewer.call_count == 2
    assert len(orchestrator.attempts) == 2
    assert len(orchestrator.review_results) == 2
    assert orchestrator.retry_explanations == ["Be more specific"]
    assert len(logger.logs) == 2


@pytest.mark.asyncio
async def test_orchestrator_fails_after_max_retries():
    """After the retry is also rejected, the orchestrator returns the last result."""
    context = DialogueContext()
    context.scope = "identify attack patterns"
    context.timeframe = "last 6 months"
    context.target_entities = ["Norway"]

    generator = MockGenerator()
    reviewer = MockReviewer(
        responses=[
            make_rejected_result(),
            make_rejected_result(),
            make_rejected_result(),
        ]
    )
    logger = MockLogger()
    orchestrator = AIOrchestrator(
        research_logger=logger,
        generator_model="test-model",
    )

    result = await orchestrator.generate_and_review_pir(
        context,
        generator,
        reviewer,
        phase="direction",
        session_id="test-session-id",
    )

    assert result == "Generated PIR based on context"
    assert reviewer.call_count == 2
    assert len(orchestrator.attempts) == 2
    assert len(orchestrator.review_results) == 2
    assert orchestrator.attempts[-1] == result
    assert len(orchestrator.retry_explanations) == 2
    assert len(logger.logs) == 2


@pytest.mark.asyncio
async def test_orchestrator_logs_generation_failures_before_reraising():
    logger = MockLogger()
    orchestrator = AIOrchestrator(research_logger=logger, generator_model="test-model")

    async def generate_fn(_feedback=None):
        raise RuntimeError("generator failed")

    with pytest.raises(RuntimeError, match="generator failed"):
        await orchestrator._run_with_review(
            generate_fn=generate_fn,
            reviewer=MockReviewer(responses=[make_approved_result()]),
            context=DialogueContext(),
            phase="direction",
            session_id="session-err",
        )

    assert len(logger.logs) == 1
    assert logger.logs[0].error_type == "RuntimeError"
    assert logger.logs[0].generated_content == ""
    assert logger.logs[0].session_id == "session-err"


@pytest.mark.asyncio
async def test_orchestrator_logs_review_failures_with_generated_content():
    class FailingReviewer:
        async def review_pir(self, content, context, phase):  # noqa: ARG002
            raise ValueError("review failed")

    logger = MockLogger()
    orchestrator = AIOrchestrator(research_logger=logger, generator_model="test-model")

    async def generate_fn(_feedback=None):
        return {"pirs": [{"question": "What access exists?"}]}

    with pytest.raises(ValueError, match="review failed"):
        await orchestrator._run_with_review(
            generate_fn=generate_fn,
            reviewer=FailingReviewer(),
            context=DialogueContext(),
            phase="direction",
            session_id="session-review-err",
        )

    assert len(logger.logs) == 1
    assert logger.logs[0].error_type == "ValueError"
    assert "What access exists?" in logger.logs[0].generated_content


@pytest.mark.asyncio
async def test_collect_and_review_returns_raw_data_after_reviewing_summary():
    class FakeCollectionService:
        def __init__(self):
            self.collect_kwargs = None
            self.summarized_raw = None

        async def collect(self, sources, pir, plan, **kwargs):  # noqa: ARG002
            self.collect_kwargs = kwargs
            return '{"collected_data": [{"source": "read_knowledge_base"}]}'

        async def summarize(self, pir, raw_data, language):  # noqa: ARG002
            self.summarized_raw = raw_data
            return '{"summary": "collection summary"}'

    collection_service = FakeCollectionService()
    reviewer = MockReviewer(responses=[make_approved_result()])
    orchestrator = AIOrchestrator(research_logger=MockLogger())

    raw_data = await orchestrator.collect_and_review(
        sources=["Knowledge Bank"],
        pir="What access is being developed?",
        plan="Use the knowledge bank.",
        collection_service=collection_service,
        reviewer=reviewer,
        session_id="collection-session",
        timeframe="2026-01-01",
        perspectives=["norway"],
        source_timeframes={"Knowledge Bank": "last 90 days"},
        language="no",
    )

    assert raw_data == '{"collected_data": [{"source": "read_knowledge_base"}]}'
    assert collection_service.summarized_raw == raw_data
    assert collection_service.collect_kwargs["timeframe"] == "2026-01-01"
    assert collection_service.collect_kwargs["source_timeframes"] == {
        "Knowledge Bank": "last 90 days"
    }
    assert reviewer.call_count == 1


@pytest.mark.asyncio
async def test_analyse_and_review_reconstructs_validated_models():
    finding = FindingModel(
        id="f1",
        title="Credential access",
        finding="Privileged credentials were targeted.",
        evidence_summary="Authentication logs show repeated attempts.",
        source="network_telemetry",
        confidence=80,
        why_it_matters="Identity access creates follow-on risk.",
    )
    processing_result = ProcessingResult(findings=[finding], gaps=["Attribution gap"])
    draft = AnalysisDraft(
        title="Telecom access risk",
        summary="Credential activity creates telecom access risk.",
        key_judgments=["Privileged access is the priority risk."],
        per_perspective_implications={},
        recommended_actions=["Review privileged access."],
        information_gaps=["Attribution gap"],
    )

    class FakeAnalysisService:
        async def generate_draft(
            self,
            processing_result,
            pir,
            selected_perspectives,
            language,
        ):  # noqa: ARG002
            return draft, processing_result

    orchestrator = AIOrchestrator(research_logger=MockLogger())

    result_draft, result_processing = await orchestrator.analyse_and_review(
        processing_result=processing_result,
        analysis_service=FakeAnalysisService(),
        reviewer=MockReviewer(responses=[make_approved_result()]),
        session_id="analysis-session",
        pir="What is the threat?",
        selected_perspectives=["neutral"],
        language="en",
    )

    assert isinstance(result_draft, AnalysisDraft)
    assert isinstance(result_processing, ProcessingResult)
    assert result_draft.title == "Telecom access risk"
    assert result_processing.findings[0].id == "f1"


@pytest.mark.asyncio
async def test_process_and_review_marks_context_as_revision_when_previous_result_exists():
    class CapturingReviewer:
        def __init__(self):
            self.context = None

        async def review_pir(self, content, context, phase):  # noqa: ARG002
            self.context = context
            return make_approved_result()

    class FakeProcessingService:
        def __init__(self):
            self.previous_result = None

        async def process(
            self,
            collected_data,
            pir,
            feedback,
            previous_result,
            language,
        ):  # noqa: ARG002
            self.previous_result = previous_result
            return "processed result"

    reviewer = CapturingReviewer()
    processing_service = FakeProcessingService()
    orchestrator = AIOrchestrator(research_logger=MockLogger())

    result = await orchestrator.process_and_review(
        collected_data="raw collection",
        pir="What access exists?",
        processing_service=processing_service,
        reviewer=reviewer,
        session_id="processing-session",
        previous_result="older processing result",
        language="en",
    )

    assert result == "processed result"
    assert reviewer.context.is_revision is True
    assert processing_service.previous_result == "older processing result"


@pytest.mark.asyncio
async def test_run_with_review_unwraps_exception_group_and_reraises_inner():
    # arrange
    logger = MockLogger()
    orchestrator = AIOrchestrator(research_logger=logger)

    async def generate_fn(_feedback=None):
        raise ExceptionGroup("wrapped", [ValueError("root cause")])

    # act / assert
    with pytest.raises(ValueError, match="root cause"):
        await orchestrator._run_with_review(
            generate_fn=generate_fn,
            reviewer=MockReviewer(responses=[make_approved_result()]),
            context=DialogueContext(),
            phase="direction",
            session_id="eg-session",
        )

    assert logger.logs[0].error_type == "ValueError"


@pytest.mark.asyncio
async def test_collect_and_review_accumulates_data_across_two_attempts():
    # arrange
    call_count = {"n": 0}

    class FakeCollectionService:
        async def collect(self, sources, pir, plan, **kwargs):  # noqa: ARG002
            call_count["n"] += 1
            return f'{{"collected_data": [{{"source": "kb", "attempt": {call_count["n"]}}}]}}'

        async def summarize(self, pir, raw_data, language):  # noqa: ARG002
            return '{"summary": "summary"}'

    orchestrator = AIOrchestrator(research_logger=MockLogger())
    orchestrator.max_attempts = 2
    reviewer = MockReviewer(responses=[make_rejected_result(), make_approved_result()])

    # act
    raw_data = await orchestrator.collect_and_review(
        sources=["Knowledge Bank"],
        pir="What access exists?",
        plan="Check KB.",
        collection_service=FakeCollectionService(),
        reviewer=reviewer,
        session_id="multi-attempt-session",
    )

    # assert — second attempt appended after separator
    assert "--- NEW COLLECTION ATTEMPT ---" in raw_data
    assert call_count["n"] == 2
