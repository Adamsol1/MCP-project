"""Shared test fixtures for services tests.

MockGenerator and MockReviewer are used by both test_ai_orchestrator.py
and test_reasoning_logger.py. Defined here once to avoid duplication.
"""

from src.models.dialogue import PIRReview, ReviewResult


def make_approved_result() -> ReviewResult:
    """Helper: lager et godkjent ReviewResult for bruk i tester."""
    return ReviewResult(
        overall_approved=True,
        pir_reviews=[PIRReview(pir_index=0, approved=True, issue=None)],
        severity="none",
        suggestions=None,
    )


def make_rejected_result() -> ReviewResult:
    """Helper: lager et avvist ReviewResult (major) for bruk i tester."""
    return ReviewResult(
        overall_approved=False,
        pir_reviews=[
            PIRReview(pir_index=0, approved=False, issue="Does not meet SMART criteria")
        ],
        severity="major",
        suggestions="Be more specific",
    )


# Mock AI1, generates PIR from context
class MockGenerator:
    async def generate_pir(self, context):  # noqa: ARG002
        return "Generated PIR based on context"


# Mock AI2, reviews PIR and returns ReviewResult
# responses: liste av ReviewResult, én per kall
# Eksempel: [make_rejected_result(), make_approved_result()] = avviser første, godkjenner andre
class MockReviewer:
    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0

    async def review_pir(self, pir_report, context, phase):  # noqa: ARG002
        result = self.responses[self.call_count]
        self.call_count += 1
        return result


# Mock logger, stores log entries in memory instead of writing to file. Only used for testing purposes
class MockLogger:
    def __init__(self):
        self.logs = []

    def create_log(self, log_entry):
        self.logs.append(log_entry)
