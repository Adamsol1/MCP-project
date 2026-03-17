import json
import logging
import time
from datetime import datetime
from typing import Any, Callable

from src.models.dialogue import CollectionContext
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

    def __init__(
        self,
        research_logger=None,
        generator_model: str = "unknown",
        reviewer_model: str = "unknown",
    ):
        self.max_retries = 1
        self.research_logger = research_logger
        self.generator_model = generator_model
        self.reviewer_model = reviewer_model
        self.attempts: list = []
        self.review_results: list[dict] = []
        self.retry_explanations: list[str] = []

    # Generic retry-and-review core used by all phase-specific methods below.
    # Arguments:
    # - generate_fn : async callable with no args — caller binds phase-specific args via lambda
    # - Reviewer    : AI that will review the generated content
    # - context     : Pydantic BaseModel passed through to reviewer unchanged
    async def _run_with_review(
        self, generate_fn: Callable, reviewer, context, phase: str, session_id: str
    ) -> Any:
        """Generic generate-and-review loop with automatic retry on major issues.

            Each generate and review attempt goes as following:
                1. Calls generate_fn() to produce content
                2. Calls reviewer.review_pir(content, context, phase)
                3. Returns content if severity != "major", otherwise retries
                + Each attempt is logged via research_logger

        Args:
            generate_fn: Async callable that accepts optional feedback (str | None).
                         First call receives None; retries receive reviewer suggestions.
                         Caller binds all phase-specific args via lambda before passing in.
            reviewer:    Service with a review_pir(content, context, phase) method.
            context:     Pydantic BaseModel passed through to reviewer unchanged.
            phase:       Intelligence cycle phase (e.g. "direction", "collection").
            session_id:  Used for logging.

        Returns:
            The generated content (str or dict) from the last approved attempt.

        Raises:
            Any exception from generate_fn or review_pir

        """
        current_retries = 0
        self.attempts = []
        self.review_results = []
        self.retry_explanations = []
        feedback: str | None = None
        # While loop that auto retries the generating and review.
        while current_retries < self.max_retries:
            attempt_timestamp = datetime.now()
            error_type: str | None = None
            generated = None
            generation_duration = 0.0
            review_duration = 0.0
            result = None

            # ---- STEP 1: Generate content (pass reviewer feedback on retries)
            logger.info(
                f"[Orchestrator] Attempt {current_retries + 1}/{self.max_retries} — generating ({phase})..."
            )
            generation_start = time.time()
            try:
                generated = await generate_fn(feedback)
            # If failed, throw error
            except Exception as e:
                generation_duration = time.time() - generation_start
                error_type = type(e).__name__
                logger.error(
                    f"[Orchestrator] Generation failed on attempt {current_retries + 1}: {error_type}: {e}"
                )
                current_retries += 1
                # Log the attempt
                log_entry = ReasoningLogEntry(
                    attempt_number=current_retries,
                    timestamp=attempt_timestamp,
                    phase=phase,
                    generated_content="",
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
            self.attempts.append(generated)
            generation_duration = time.time() - generation_start
            logger.info(f"[Orchestrator] Generated in {generation_duration:.2f}s")

            # --- Step 2 : Reviews and returns a boolean value
            review_start = time.time()
            try:
                result = await reviewer.review_pir(generated, context, phase)
            except Exception as e:
                review_duration = time.time() - review_start
                error_type = type(e).__name__
                logger.error(
                    f"[Orchestrator] Review failed on attempt {current_retries + 1}: {error_type}: {e}"
                )
                current_retries += 1
                log_entry = ReasoningLogEntry(
                    attempt_number=current_retries,
                    timestamp=attempt_timestamp,
                    phase=phase,
                    generated_content=json.dumps(generated) if isinstance(generated, dict) else generated,
                    generation_duration=generation_duration,
                    review_result=None,
                    review_duration=review_duration,
                    session_id=session_id,
                    model_used=self.generator_model,
                    error_type=error_type,
                )
                # Check if logger exist. If yes, log the entry
                if self.research_logger is not None:
                    self.research_logger.create_log(log_entry)
                raise
            review_duration = time.time() - review_start
            self.review_results.append(
                {
                    "approved": result.overall_approved,
                    "severity": result.severity,
                    "suggestions": result.suggestions,
                }
            )
            # Log retry explanation if the severity indicates a retry
            if result.suggestions and result.severity == "major":
                self.retry_explanations.append(result.suggestions)
            logger.info(
                f"[Orchestrator] Review done in {review_duration:.2f}s — approved={result.overall_approved}, severity={result.severity}"
            )
            current_retries += 1

            # Log attempt regardless of outcome
            if result.suggestions:
                logger.debug(f"[Orchestrator] Suggestions: {result.suggestions}")
            log_entry = ReasoningLogEntry(
                attempt_number=current_retries,
                timestamp=attempt_timestamp,
                phase=phase,
                generated_content=json.dumps(generated) if isinstance(generated, dict) else generated,
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
            # --- Step 3: If approved return content.
            #            If not approved -> retry
            if result.severity != "major":
                logger.info(f"[Orchestrator] Approved on attempt {current_retries}")
                return generated
            # Pass reviewer suggestions as feedback to next attempt
            feedback = result.suggestions
            logger.warning(f"[Orchestrator] Rejected (major) — retrying with feedback...")
        # If max retries are reached return current result. This is to prevent eternal loops
        logger.warning("[Orchestrator] Max retries reached. Returning newest result")
        return generated

    # Method for generating and reviewing PIR — Direction phase
    # Arguments:
    # - Generator : AI that will generate PIR
    # - Reviewer : AI that will review PIR
    async def generate_and_review_pir(
        self, context, generator, reviewer, phase: str, session_id: str
    ):
        """Generate a PIR and review it, with automatic retry on major issues.

        Args:
            context:    DialogueContext with the gathered intelligence requirements.
            generator:  Service with a generate_pir(context) method.
            reviewer:   Service with a review_pir(content, context, phase) method.
            phase:      Intelligence phase (e.g. "direction"), passed to the reviewer.
            session_id: Used for logging.

        Returns:
            The generated PIR as a str or dict.

        Raises:
            Any exception from generate_pir or review_pir
        """
        return await self._run_with_review(
            generate_fn=lambda feedback=None: generator.generate_pir(context),
            reviewer=reviewer,
            context=context,
            phase=phase,
            session_id=session_id,
        )

    # Method for collecting and reviewing intelligence data — Collection phase
    # Arguments:
    # - collection_service : AI that will collect data via tools
    # - Reviewer           : AI that will review collected data
    async def collect_and_review(
        self, sources: list, pir: str, plan: str, collection_service, reviewer, session_id: str, direction_context=None, timeframe: str = "", perspectives: list[str] | None = None
    ) -> str:
        """Collect intelligence data and review it, with automatic retry on major issues.

        Each retry accumulates data from previous attempts — the agent sees what was
        already collected and only adds new data. The reviewer always sees the full
        accumulated dataset.

        Args:
            sources:            List of selected source names.
            pir:                PIR string from the direction phase.
            plan:               Collection plan string.
            collection_service: Service with a collect(sources, pir, plan) method.
            reviewer:           Service with a review_pir(content, context, phase) method.
            session_id:         Used for logging.
            direction_context:  DialogueContext from the direction phase (optional, enriches review).
            timeframe:          PIR timeframe string used to filter OTX results by date.

        Returns:
            Accumulated raw data string from all collection attempts.

        Raises:
            Any exception from collect or review_pir
        """
        accumulated = {"raw_data": ""}

        async def collect_fn(feedback=None):
            new_data = await collection_service.collect(
                sources, pir, plan,
                feedback=feedback,
                session_id=session_id,
                timeframe=timeframe,
                existing_raw_data=accumulated["raw_data"] or None,
                perspectives=perspectives,
            )
            if accumulated["raw_data"]:
                accumulated["raw_data"] += "\n\n--- NEW COLLECTION ATTEMPT ---\n\n" + new_data
            else:
                accumulated["raw_data"] = new_data
            return accumulated["raw_data"]

        return await self._run_with_review(
            generate_fn=collect_fn,
            reviewer=reviewer,
            context=CollectionContext(pir=pir, plan=plan, direction_context=direction_context),
            phase="collection",
            session_id=session_id,
        )

    # TODO: Processing phase - AI #1 processes data, AI #2 verifies
    # async def process_and_review(self, data, processor, reviewer, session_id):
    #   Same retry pattern: process → review → retry if rejected
