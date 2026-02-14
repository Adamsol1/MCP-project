import time
from datetime import datetime
from uuid import uuid4

from src.models.reasoning import ReasoningLogEntry


class AIOrchestrator:
    def __init__(self):
        self.max_retries = 3

    # Method for generating and reviewing PIR
    # Arguments:
    # - Generator : AI that will generate PIR
    # - Reviewer : AI that will review PIR
    async def generate_and_review_pir(self, context, generator, reviewer, logger=None):
        current_retries = 0
        #Create UUID for session id
        session_id=str(uuid4())
        # While loop that auto retries the generating and review.
        while current_retries < self.max_retries:
            attempt_timestamp = datetime.now()
            # Generate PIR with given context
            generation_start = time.time()
            generated_pir = await generator.generate_pir(context)
            generation_duration = time.time() - generation_start
            # Reviews and returns a boolean value
            review_start = time.time()
            is_approved = await reviewer.review_pir(generated_pir, context)
            review_duration = time.time() - review_start
            current_retries += 1
            # TODO : add reasoning!
            log_entry = ReasoningLogEntry(
                attempt_number=current_retries,
                timestamp=attempt_timestamp,
                generated_pir=generated_pir,
                generation_duration=generation_duration,
                is_approved=is_approved,
                review_duration=review_duration,
                session_id= session_id
            )
            # Check if logger exist. If yes, log the entry
            if logger is not None:
                logger.create_log(log_entry)
            # If approved return current PIR
            if is_approved:
                return generated_pir
        # If max retries are reached return current PIR. This is to prevent eternal loops
        return generated_pir

    # TODO: Collection phase - AI #1 collects data, AI #2 validates
    # async def collect_and_review(self, pir, collector, reviewer):
    #   Same retry pattern: collect → review → retry if rejected

    # TODO: Processing phase - AI #1 processes data, AI #2 verifies
    # async def process_and_review(self, data, processor, reviewer):
    #   Same retry pattern: process → review → retry if rejected
