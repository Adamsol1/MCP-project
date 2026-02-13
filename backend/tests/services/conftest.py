"""Shared test fixtures for services tests.

MockGenerator and MockReviewer are used by both test_ai_orchestrator.py
and test_reasoning_logger.py. Defined here once to avoid duplication.
"""


# Mock AI1, generates PIR from context
class MockGenerator:
    async def generate_pir(self, context):
        return "Generated PIR based on context"


# Mock AI 2, reviews PIR and returns True/False
# responses: list of booleans, one per call
# Example: [False, True] = rejects first attempt, approves second
class MockReviewer:
    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0

    async def review_pir(self, pir_report, context):
        result = self.responses[self.call_count]
        self.call_count += 1
        return result


# Mock logger, stores log entries in memory instead of writing to file. Only used for testing purposes
class MockLogger:
    def __init__(self):
        self.logs = []

    def create_log(self, log_entry):
        self.logs.append(log_entry)
