import json
import logging
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

from src.models.analysis import AnalysisDraft, ProcessingResult
from src.models.dialogue import AnalysisContext, CollectionContext, ProcessingContext
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
        self.max_attempts = 1  # initial attempt + 1 retry on major review rejection for not only 1
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
            1. Call generate_fn(feedback),
               then the reviewer's suggestions on any retry.
            2. Call reviewer.review_pir(content, context, phase).
            3. If severity != "major", return the content.
               Otherwise pass suggestions as feedback and retry.

        Args:
            generate_fn: Async callable that accepts optional feedback (str | None).
                         Caller binds all phase specific arguments via lambda before passing in.
            reviewer:    Service with a review_pir method.
            context:     Pydantic BaseModel passed through to reviewer unchanged.
            phase:       Intelligence cycle phase.
            session_id:  Used for logging.

        Returns:
            The generated content from the last attempt.

        Raises:
            Any exception from generate_fn or review_pir.
        """
        self.attempts = []
        self.review_results = []
        self.retry_explanations = []
        feedback: str | None = None
        generated = None


        #For each attempt log generated content, review and issues.
        for attempt in range(1, self.max_attempts + 1):
            attempt_timestamp = datetime.now()
            error_type: str | None = None
            generation_duration = 0.0
            review_duration = 0.0
            result = None

            # Step 1: Generate
            logger.info(
                f"[Orchestrator] Attempt {attempt}/{self.max_attempts} — generating ({phase})..."
            )
            generation_start = time.time()
            try:
                generated = await generate_fn(feedback)
            except BaseException as e:
                #Find root cause if exception is raised
                original = e
                while isinstance(e, ExceptionGroup) and e.exceptions:
                    e = e.exceptions[0]
                if e is not original:
                    logger.error(
                        f"[Orchestrator] Unwrapped ExceptionGroup root cause: {type(e).__name__}: {e}"
                    )
                generation_duration = time.time() - generation_start
                error_type = type(e).__name__
                logger.error(
                    f"[Orchestrator] Generation failed on attempt {attempt}: {error_type}: {e}",
                    exc_info=True,
                )
                #Log the failed attempt
                self._log_attempt(
                    ReasoningLogEntry(
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
                    )
                )
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
                logger.error(
                    f"[Orchestrator] Review failed on attempt {attempt}: {error_type}: {e}"
                )
                self._log_attempt(
                    ReasoningLogEntry(
                        attempt_number=attempt,
                        timestamp=attempt_timestamp,
                        phase=phase,
                        generated_content=json.dumps(generated)
                        if isinstance(generated, dict)
                        else generated,
                        generation_duration=generation_duration,
                        review_result=None,
                        review_duration=review_duration,
                        session_id=session_id,
                        model_used=self.generator_model,
                        error_type=error_type,
                    )
                )
                raise
            review_duration = time.time() - review_start

            self.review_results.append(
                {
                    "approved": result.overall_approved,
                    "severity": result.severity,
                    "suggestions": result.suggestions,
                }
            )
            logger.info(
                f"[Orchestrator] Review done in {review_duration:.2f}s"
                f"approved={result.overall_approved}, severity={result.severity}"
            )
            if result.suggestions:
                logger.debug(f"[Orchestrator] Suggestions: {result.suggestions}")

            self._log_attempt(
                ReasoningLogEntry(
                    attempt_number=attempt,
                    timestamp=attempt_timestamp,
                    phase=phase,
                    generated_content=json.dumps(generated)
                    if isinstance(generated, dict)
                    else generated,
                    generation_duration=generation_duration,
                    review_result=result,
                    review_duration=review_duration,
                    session_id=session_id,
                    model_used=self.generator_model,
                    error_type=error_type,
                )
            )

            # Step 3: Accept or retry
            if result.severity != "major":
                logger.info(f"[Orchestrator] Accepted on attempt {attempt}")
                return generated

            feedback = result.suggestions
            self.retry_explanations.append(result.suggestions or "")
            logger.warning(
                f"[Orchestrator] Rejected (major) on attempt {attempt} retring with feedvack"
            )

        logger.warning(
            f"[Orchestrator] All {self.max_attempts} Too many attempts used. Returning the last result."
        )
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
            generator:  Service with a generate_pir method.
            reviewer:   Service with a review_pir method.
            phase:      Intelligence phase (e.g. "direction"), passed to the reviewer.
            session_id: Used for logging.

        Returns:
            The generated PIR as a str or dict.

        Raises:
            Any exception from generate_pir or review_pir
        """
        return await self._run_with_review(
            generate_fn=lambda _feedback=None: generator.generate_pir(context),
            reviewer=reviewer,
            context=context,
            phase=phase,
            session_id=session_id,
        )

    async def collect_and_review(
        self,
        sources: list,
        pir: str,
        plan: str,
        collection_service,
        reviewer,
        session_id: str,
        direction_context=None,
        timeframe: str = "",
        perspectives: list[str] | None = None,
        feedback: str | None = None,
        source_timeframes: dict[str, str] | None = None,
        language: str = "en",
    ) -> str:
        """Collect intelligence data and review it, with automatic retry on major issues.

        Each retry uses data from the previus attempt meaning that the agent adds to already collected data. All data is given to the reviewer

        Args:
            sources:            List of selected sources.
            pir:                PIR string from the direction phase.
            plan:               Collection plan string.
            collection_service: Service with a collect method.
            reviewer:           Service with a review_pir method.
            session_id:         Used for logging.
            direction_context:  DialogueContext from the direction phase.
            timeframe:          PIR timeframe. Used to filter results.

        Returns:
            All raw data from collection.

        Raises:
            Any exception from collect or review_pir
        """
        accumulated = {"raw_data": ""}

        async def collect_fn(reviewer_feedback=None):
            new_data = await collection_service.collect(
                sources,
                pir,
                plan,
                feedback=reviewer_feedback or feedback,
                session_id=session_id,
                timeframe=timeframe,
                existing_raw_data=accumulated["raw_data"] or None,
                perspectives=perspectives,
                source_timeframes=source_timeframes,
                language=language,
            )
            if accumulated["raw_data"]:
                accumulated["raw_data"] += (
                    "\n\n--- NEW COLLECTION ATTEMPT ---\n\n" + new_data
                )
            else:
                accumulated["raw_data"] = new_data
            # Summarize before passing to reviewer
            # instead of the raw collection data
            return await collection_service.summarize(pir, accumulated["raw_data"], language)

        await self._run_with_review(
            generate_fn=collect_fn,
            reviewer=reviewer,
            context=CollectionContext(
                pir=pir,
                plan=plan,
                direction_context=direction_context,
                gather_more_feedback=feedback,
            ),
            phase="collection",
            session_id=session_id,
        )
        # Always return raw data
        return accumulated["raw_data"]

    async def analyse_and_review(
        self,
        processing_result,
        analysis_service,
        reviewer,
        session_id: str,
        pir: str = "",
        selected_perspectives: list[str] | None = None,
        language: str = "en",
    ) -> tuple:
        """
        Generate analysis and review it. If the reviewer finds errors, regenerate

        Args:
            processing_result : ProcessingResult
            analysis_service : Service
            reviewer : Service with a review_pir method
            session_id : Used for logging.
            pir : PIR string from direction phase.
            selected_perspectives : Perspectives to include in the analysis.

        Returns:
            Tuple of (AnalysisDraft, enriched ProcessingResult)
        """
        async def analyse_fn(_=None):
            draft, enriched = await analysis_service.generate_draft(
                processing_result,
                pir=pir,
                selected_perspectives=selected_perspectives,
                language=language,
            )
            return {
                "analysis_draft": draft.model_dump(),
                "processing_result": enriched.model_dump(),
            }

        result = await self._run_with_review(
            generate_fn=analyse_fn,
            reviewer=reviewer,
            context=AnalysisContext(
                pir=pir,
                processing_result=processing_result.model_dump(),
            ),
            phase="analysis",
            session_id=session_id,
        )

        analysis_draft = AnalysisDraft.model_validate(result["analysis_draft"])
        enriched_result = ProcessingResult.model_validate(result["processing_result"])
        return analysis_draft, enriched_result

    async def process_and_review(
        self,
        collected_data: str,
        pir: str,
        processing_service,
        reviewer,
        session_id: str,
        previous_result: str | None = None,
        language: str = "en",
    ) -> str:
        """
        Process collected data and review it. If the reviewer rejects, regenerate.

        Args:
            collected_data : Raw collected data
            pir : PIR string
            processing_service : Service with a process method.
            reviewer : Service with a review_pir method.
            session_id : Used for logging.
            previous_result : Previous processing result if this is a revision.

        Returns:
            Processed result string.
        """
        async def process_fn(feedback=None):
            return await processing_service.process(
                collected_data=collected_data,
                pir=pir,
                feedback=feedback,
                previous_result=previous_result,
                language=language,
            )

        return await self._run_with_review(  # type: ignore[no-any-return]
            generate_fn=process_fn,
            reviewer=reviewer,
            context=ProcessingContext(
                pir=pir,
                collected_data=collected_data,
                is_revision=previous_result is not None,
            ),
            phase="processing",
            session_id=session_id,
        )
