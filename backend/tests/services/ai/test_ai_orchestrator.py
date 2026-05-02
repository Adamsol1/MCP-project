# Tests for AI Orchestrator - coordinates AI #1 (generate) and AI #2 (review)

import pytest

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
    """With max_attempts=1, the orchestrator runs one attempt and returns the result
    even if the reviewer rejects it (no retry occurs)."""
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
    assert reviewer.call_count == 1
    assert len(orchestrator.attempts) == 1
    assert len(orchestrator.review_results) == 1
    assert orchestrator.retry_explanations == ["Be more specific"]
    assert len(logger.logs) == 1


@pytest.mark.asyncio
async def test_orchestrator_fails_after_max_retries():
    """With max_attempts=1, even multiple rejections result in a single attempt."""
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
    assert reviewer.call_count == 1
    assert len(orchestrator.attempts) == 1
    assert len(orchestrator.review_results) == 1
    assert orchestrator.attempts[-1] == result
    assert len(orchestrator.retry_explanations) == 1
    assert len(logger.logs) == 1
