import json
import time
from datetime import datetime
from uuid import uuid4

from src.models.reasoning import ReasoningLogEntry


class AIOrchestrator:
    def __init__(self, logger=None):
        self.max_retries = 3
        self.logger = logger

    # Method for generating and reviewing PIR
    # Arguments:
    # - Generator : AI that will generate PIR
    # - Reviewer : AI that will review PIR
    async def generate_and_review_pir(self, context, generator, reviewer, phase):
        current_retries = 0
        #Create UUID for session id
        session_id=str(uuid4())
        # While loop that auto retries the generating and review.
        while current_retries < self.max_retries:
            attempt_timestamp = datetime.now()
            # Generate PIR with given context
            generation_start = time.time()
            print(f"[Orchestrator] Attempt {current_retries + 1}/{self.max_retries} — generating PIR...", flush=True)  # TODO: remove
            generated_pir = await generator.generate_pir(context)
            generation_duration = time.time() - generation_start
            print(f"[Orchestrator] PIR generated in {generation_duration:.2f}s", flush=True)  # TODO: remove
            # Reviews and returns a boolean value
            review_start = time.time()
            print("[Orchestrator] Sending PIR to reviewer...", flush=True)  # TODO: remove  # noqa: E501
            result = await reviewer.review_pir(generated_pir, context, phase)
            review_duration = time.time() - review_start
            print(f"[Orchestrator] Review done in {review_duration:.2f}s — approved={result.overall_approved}, severity={result.severity}", flush=True)  # TODO: remove
            if result.suggestions:
                print(f"[Orchestrator] Suggestions: {result.suggestions}", flush=True)  # TODO: remove
            current_retries += 1
            log_entry = ReasoningLogEntry(
                attempt_number=current_retries,
                timestamp=attempt_timestamp,
                generated_pir=json.dumps(generated_pir) if isinstance(generated_pir, dict) else generated_pir,
                generation_duration=generation_duration,
                review_result=result,
                review_duration=review_duration,
                session_id= session_id
            )
            # Check if logger exist. If yes, log the entry
            if self.logger is not None:
                self.logger.create_log(log_entry)
            # If approved return current PIR
            if result.severity != "major":
                print(f"[Orchestrator] PIR approved on attempt {current_retries} — returning.", flush=True)  # TODO: remove
                return generated_pir
            print("[Orchestrator] PIR rejected (major) — retrying...", flush=True)  # TODO: remove
        # If max retries are reached return current PIR. This is to prevent eternal loops
        print("[Orchestrator] Max retries reached — returning best PIR anyway.", flush=True)  # TODO: remove
        return generated_pir

    # TODO: Collection phase - AI #1 collects data, AI #2 validates
    # async def collect_and_review(self, pir, collector, reviewer):
    #   Same retry pattern: collect → review → retry if rejected

    # TODO: Processing phase - AI #1 processes data, AI #2 verifies
    # async def process_and_review(self, data, processor, reviewer):
    #   Same retry pattern: process → review → retry if rejected
