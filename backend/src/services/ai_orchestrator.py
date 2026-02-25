import json
import logging
import time
from datetime import datetime

from src.models.reasoning import ReasoningLogEntry

logger = logging.getLogger("app")


class AIOrchestrator:
    """
    Orchestrator that orchestrates generation and review for PIRs

    The orchestrator will run:
        - A generator AI that will generate PIR/Summary
        - A reviwer AI that will review PIR/summary

    Each attempt is logged to the researchLogger for auditing
    """
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
        """
        async def generate_and_review_pir(self, context, generator, reviewer, phase, session_id: str):

        Generate a PIR and review it. If reviwer find major issues -> retry

        Each generate and review attemps goes as following:
            1. Calls generator.generate_pir(context)
            2. Calls reviewer.review_pir(pir, context, phase)
            3. Returns the PIR if severity != "major", otherwise retries
            + Each attempt is logged via research_logger

    Args:
        context:    DialogueContext with the gathered intelligence requirements.
        generator:  Service with a generate_pir(context) method.
        reviewer:   Service with a review_pir(pir, context, phase) method.
        phase:      Intelligence phase (e.g. "direction"), passed to the reviewer.
        session_id: Used for logging.

    Returns:
        The generated PIR as a str or dict.

    Raises:
        Any exception from generate_pir or review_pir

        """
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

            # ---- STEP 1: Generate PIR with given context
            logger.info(f"[Orchestrator] Attempt {current_retries + 1}/{self.max_retries} — generating PIR...")
            generation_start = time.time()
            try:
                generated_pir = await generator.generate_pir(context)
            #If failed, throw error
            except Exception as e:
                generation_duration = time.time() - generation_start
                error_type = type(e).__name__
                logger.error(f"[Orchestrator] Generation failed on attempt {current_retries + 1}: {error_type}: {e}")
                current_retries += 1
                #Log the attempt
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

            # --- Step 2 : Reviews and returns a boolean value
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
                #Check if logger exist. If yes, log the entry
                if self.research_logger is not None:
                    self.research_logger.create_log(log_entry)
                raise
            review_duration = time.time() - review_start
            self.review_results.append({
                "approved": result.overall_approved,
                "severity": result.severity,
                "suggestions": result.suggestions,
                })
            #Log retry if explanation if the severity indicates a retry
            if result.suggestions and result.severity == "major":
                self.retry_explanations.append(result.suggestions)
            logger.info(f"[Orchestrator] Review done in {review_duration:.2f}s — approved={result.overall_approved}, severity={result.severity}")
            current_retries += 1

            #Log attempt regardles of outcome
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
            #--- Step 3: If approved return current PIR.
            #            If not approved -> retry
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
