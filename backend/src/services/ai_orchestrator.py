import json
import time
from datetime import datetime
import logging
logger = logging.getLogger("app")

from src.models.reasoning import ReasoningLogEntry


class AIOrchestrator:
    def __init__(self, research_logger=None, generator_model: str = "unknown", reviewer_model: str = "unknown"):
        self.max_retries = 3
        self.research_logger = research_logger
        self.generator_model = generator_model
        self.reviewer_model = reviewer_model
        self.generated_pirs: list = []
        self.review_results: list[dict] = []
        self.retry_explanations: list[str] = []

    # Method for generating and reviewing PIR
    # Arguments:
    # - Generator : AI that will generate PIR
    # - Reviewer : AI that will review PIR
    async def generate_and_review_pir(self, context, generator, reviewer, phase, session_id: str):
        current_retries = 0
        self.generated_pirs = []
        self.review_results = []
        self.retry_explanations = []
        # While loop that auto retries the generating and review.
        while current_retries < self.max_retries:
            attempt_timestamp = datetime.now()
            error_type: str | None = None
            generated_pir = None
            generation_duration = 0.0
            review_duration = 0.0
            result = None

            # Generate PIR with given context
            logger.info(f"[Orchestrator] Attempt {current_retries + 1}/{self.max_retries} — generating PIR...")
            generation_start = time.time()
            try:
                generated_pir = await generator.generate_pir(context)
            except Exception as e:
                generation_duration = time.time() - generation_start
                error_type = type(e).__name__
                logger.error(f"[Orchestrator] Generation failed on attempt {current_retries + 1}: {error_type}: {e}")
                current_retries += 1
                log_entry = ReasoningLogEntry(
                    attempt_number=current_retries,
                    timestamp=attempt_timestamp,
                    generated_pir="",
                    generation_duration=generation_duration,
                    review_result=None,
                    review_duration=0.0,
                    session_id=session_id,
                    model_used=self.generator_model,
                    error_type=error_type,
                )
                if self.research_logger is not None:
                    self.research_logger.create_log(log_entry)
                raise
            self.generated_pirs.append(generated_pir)
            generation_duration = time.time() - generation_start
            logger.info(f"[Orchestrator] PIR generated in {generation_duration:.2f}s")

            # Reviews and returns a boolean value
            review_start = time.time()
            try:
                result = await reviewer.review_pir(generated_pir, context, phase)
            except Exception as e:
                review_duration = time.time() - review_start
                error_type = type(e).__name__
                logger.error(f"[Orchestrator] Review failed on attempt {current_retries + 1}: {error_type}: {e}")
                current_retries += 1
                log_entry = ReasoningLogEntry(
                    attempt_number=current_retries,
                    timestamp=attempt_timestamp,
                    generated_pir=json.dumps(generated_pir) if isinstance(generated_pir, dict) else generated_pir,
                    generation_duration=generation_duration,
                    review_result=None,
                    review_duration=review_duration,
                    session_id=session_id,
                    model_used=self.generator_model,
                    error_type=error_type,
                )
                if self.research_logger is not None:
                    self.research_logger.create_log(log_entry)
                raise
            review_duration = time.time() - review_start
            self.review_results.append({
                "approved": result.overall_approved,
                "severity": result.severity,
                "suggestions": result.suggestions,
                })
            if result.suggestions and result.severity == "major":
                self.retry_explanations.append(result.suggestions)
            logger.info(f"[Orchestrator] Review done in {review_duration:.2f}s — approved={result.overall_approved}, severity={result.severity}")
            current_retries += 1
            if result.suggestions:
                logger.debug(f"[Orchestrator] Suggestions: {result.suggestions}")
            log_entry = ReasoningLogEntry(
                attempt_number=current_retries,
                timestamp=attempt_timestamp,
                generated_pir=json.dumps(generated_pir) if isinstance(generated_pir, dict) else generated_pir,
                generation_duration=generation_duration,
                review_result=result,
                review_duration=review_duration,
                session_id=session_id,
                model_used=self.generator_model,
                error_type=error_type,
            )
            # Check if logger exist. If yes, log the entry
            if self.research_logger is not None:
                self.research_logger.create_log(log_entry)
            # If approved return current PIR
            if result.severity != "major":
                logger.info(f"[Orchestrator] PIR approved on attempt {current_retries}")
                return generated_pir
            logger.warning("[Orchestrator] PIR rejected (major) — retrying...")
        # If max retries are reached return current PIR. This is to prevent eternal loops
        logger.warning("[Orchestrator] Max retries reached. Returning newest pir")
        return generated_pir

    # TODO: Collection phase - AI #1 collects data, AI #2 validates
    # async def collect_and_review(self, pir, collector, reviewer):
    #   Same retry pattern: collect → review → retry if rejected

    # TODO: Processing phase - AI #1 processes data, AI #2 verifies
    # async def process_and_review(self, data, processor, reviewer):
    #   Same retry pattern: process → review → retry if rejected
