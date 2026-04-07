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
        self.max_attempts = 2  # initial attempt + 1 retry on major review rejection
        self.research_logger = research_logger
        self.generator_model = generator_model
        self.reviewer_model = reviewer_model
        self.attempts: list = []
        self.review_results: list[dict] = []
        self.retry_explanations: list[str] = []

    async def _run_with_review(
        self, generate_fn: Callable, reviewer, context, phase: str, session_id: str
    ) -> Any:
        """Generate content and review it, retrying once if the reviewer flags a major issue.

        Flow per attempt:
            1. Call generate_fn(feedback) — feedback is None on the first attempt,
               then the reviewer's suggestions on any retry.
            2. Call reviewer.review_pir(content, context, phase).
            3. If severity != "major", return the content.
               Otherwise pass suggestions as feedback and retry.

        Args:
            generate_fn: Async callable that accepts optional feedback (str | None).
                         Caller binds all phase-specific args via lambda before passing in.
            reviewer:    Service with a review_pir(content, context, phase) method.
            context:     Pydantic BaseModel passed through to reviewer unchanged.
            phase:       Intelligence cycle phase (e.g. "direction", "collection").
            session_id:  Used for logging.

        Returns:
            The generated content (str or dict) from the last attempt.

        Raises:
            Any exception from generate_fn or review_pir.
        """
        self.attempts = []
        self.review_results = []
        self.retry_explanations = []
        feedback: str | None = None
        generated = None

        for attempt in range(1, self.max_attempts + 1):
            attempt_timestamp = datetime.now()
            error_type: str | None = None
            generation_duration = 0.0
            review_duration = 0.0
            result = None

            # Step 1: Generate
            logger.info(f"[Orchestrator] Attempt {attempt}/{self.max_attempts} — generating ({phase})...")
            generation_start = time.time()
            try:
                generated = await generate_fn(feedback)
            except BaseException as e:
                # Unwrap nested ExceptionGroups to find the root cause
                original = e
                while isinstance(e, ExceptionGroup) and e.exceptions:
                    e = e.exceptions[0]
                if e is not original:
                    logger.error(f"[Orchestrator] Unwrapped ExceptionGroup root cause: {type(e).__name__}: {e}")
                generation_duration = time.time() - generation_start
                error_type = type(e).__name__
                logger.error(f"[Orchestrator] Generation failed on attempt {attempt}: {error_type}: {e}")
                self._log_attempt(ReasoningLogEntry(
                    attempt_number=attempt,
                    timestamp=attempt_timestamp,
                    phase=phase,
                    generated_content="",
                    generation_duration=generation_duration,
                    review_result=None,
                    review_duration=0.0,
                    session_id=session_id,
                    model_used=self.generator_model,
                    error_type=error_type,
                ))
                raise
            self.attempts.append(generated)
            generation_duration = time.time() - generation_start
            logger.info(f"[Orchestrator] Generated in {generation_duration:.2f}s")

            # Step 2: Review
            review_start = time.time()
            try:
                result = await reviewer.review_pir(generated, context, phase)
            except Exception as e:
                review_duration = time.time() - review_start
                error_type = type(e).__name__
                logger.error(f"[Orchestrator] Review failed on attempt {attempt}: {error_type}: {e}")
                self._log_attempt(ReasoningLogEntry(
                    attempt_number=attempt,
                    timestamp=attempt_timestamp,
                    phase=phase,
                    generated_content=json.dumps(generated) if isinstance(generated, dict) else generated,
                    generation_duration=generation_duration,
                    review_result=None,
                    review_duration=review_duration,
                    session_id=session_id,
                    model_used=self.generator_model,
                    error_type=error_type,
                ))
                raise
            review_duration = time.time() - review_start

            self.review_results.append({
                "approved": result.overall_approved,
                "severity": result.severity,
                "suggestions": result.suggestions,
            })
            logger.info(
                f"[Orchestrator] Review done in {review_duration:.2f}s — "
                f"approved={result.overall_approved}, severity={result.severity}"
            )
            if result.suggestions:
                logger.debug(f"[Orchestrator] Suggestions: {result.suggestions}")

            self._log_attempt(ReasoningLogEntry(
                attempt_number=attempt,
                timestamp=attempt_timestamp,
                phase=phase,
                generated_content=json.dumps(generated) if isinstance(generated, dict) else generated,
                generation_duration=generation_duration,
                review_result=result,
                review_duration=review_duration,
                session_id=session_id,
                model_used=self.generator_model,
                error_type=error_type,
            ))

            # Step 3: Accept or retry
            if result.severity != "major":
                logger.info(f"[Orchestrator] Accepted on attempt {attempt}")
                return generated

            feedback = result.suggestions
            self.retry_explanations.append(result.suggestions)
            logger.warning(f"[Orchestrator] Rejected (major) on attempt {attempt} — retrying with feedback...")

        logger.warning(f"[Orchestrator] All {self.max_attempts} attempts exhausted. Returning last result.")
        return generated

    def _log_attempt(self, entry: ReasoningLogEntry) -> None:
        if self.research_logger is not None:
            self.research_logger.create_log(entry)

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

    async def process_and_review(
        self,
        collected_data: str,
        pir: str,
        processing_service,
        reviewer,
        session_id: str,
    ) -> str:
        async def process_fn(feedback=None):
            return await processing_service.process(
                collected_data=collected_data,
                pir=pir,
                feedback=feedback,
            )

        from src.models.dialogue import ProcessingContext
        return await self._run_with_review(
            generate_fn=process_fn,
            reviewer=reviewer,
            context=ProcessingContext(pir=pir, collected_data=collected_data),
            phase="processing",
            session_id=session_id,
        )
