# Tests for AI Orchestrator - coordinates AI #1 (generate) and AI #2 (review)

import pytest

from src.models.dialogue import DialogueContext
from src.services.ai_orchestrator import AIOrchestrator
from tests.services.conftest import MockGenerator, MockReviewer


# Test for checking if orchestrator approves
@pytest.mark.asyncio
async def test_orchestrator_approves_on_first_try():
    # Create context
    context = DialogueContext()
    context.scope = "identify attack patterns"
    context.timeframe = "last 6 months"
    context.target_entities = ["Norway"]

    # Create enviorment for testing
    generator = MockGenerator()
    reviewer = MockReviewer(responses=[True])
    orchestrator = AIOrchestrator()

    # Call method
    result = await orchestrator.generate_and_review_pir(
        context, generator, reviewer, logger=None
    )

    # Test result
    assert result


# Test for checking correct behaviour when first PIR is rejected, and the second one is approved
@pytest.mark.asyncio
async def test_orchestrator_retries_and_succeeds():
    # Create context
    context = DialogueContext()
    context.scope = "identify attack patterns"
    context.timeframe = "last 6 months"
    context.target_entities = ["Norway"]

    # Create enivorment
    generator = MockGenerator()
    # First one is rejected, second one is accepted
    reviewer = MockReviewer(responses=[False, True])
    orchestrator = AIOrchestrator()

    # Generate the PIR and review
    result = await orchestrator.generate_and_review_pir(
        context, generator, reviewer, logger=None
    )

    # Test result
    assert result


# Test for checking max retries
@pytest.mark.asyncio
async def test_orchestrator_fails_after_max_retries():
    # Create context
    context = DialogueContext()
    context.scope = "identify attack patterns"
    context.timeframe = "last 6 months"
    context.target_entities = ["Norway"]

    # Create test enviorment
    generator = MockGenerator()
    reviewer = MockReviewer(responses=[False, False, False])
    orchestrator = AIOrchestrator()

    # Call method
    result = await orchestrator.generate_and_review_pir(
        context, generator, reviewer, logger=None
    )

    # Check if rejected
    assert result  # PIR sendes videre uansett
    assert reviewer.call_count == 3  # Prøvde 3 ganger
