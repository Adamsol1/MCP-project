"""ProcessingFlow — state machine for the Processing phase.

Reads raw collected data from collection_attempts table, runs the processing agent
(normalize → enrich → correlate → synthesize), writes the result to
processing_attempts table, and presents it for analyst review.

States:
    PROCESSING  — agent has not yet run (waiting for initialize)
    REVIEWING   — analyst is reviewing the processed result
    COMPLETE    — analyst approved, phase done
"""

import json
import logging
from datetime import UTC, datetime
from enum import Enum

from src.models.dialogue import DialogueAction, DialogueContext, DialogueResponse, PhaseReviewItem
from src.models.reasoning import ReasoningLog
from src.services.state_machines.base_phase_flow import BasePhaseFlow

logger = logging.getLogger("app")

_PHASE_PROCESSING = "processing"


async def _read_collected(session_id: str, uow=None) -> dict | None:
    """Read collected data from DB via UoW."""
    if uow is None:
        raise RuntimeError(f"[ProcessingFlow] UoW required to read collected data for {session_id}")
    try:
        attempts = await uow.collection_attempts.get_all(session_id)
        if not attempts:
            return None
        return {
            "session_id": session_id,
            "pir": attempts[0].pir,
            "collected_at": attempts[0].created_at.isoformat() if attempts[0].created_at else "",
            "updated_at": attempts[-1].created_at.isoformat() if attempts[-1].created_at else "",
            "attempts": [a.raw_response for a in attempts],
        }
    except Exception:
        logger.exception(f"[ProcessingFlow] Failed to read collected data from DB for {session_id}")
        return None


async def _read_processed(session_id: str, uow=None) -> dict | None:
    """Read processed data from DB via UoW."""
    if uow is None:
        raise RuntimeError(f"[ProcessingFlow] UoW required to read processed data for {session_id}")
    try:
        attempts = await uow.processing_attempts.get_all(session_id)
        if not attempts:
            return None
        return {
            "session_id": session_id,
            "pir": attempts[0].pir,
            "processed_at": attempts[0].created_at.isoformat() if attempts[0].created_at else "",
            "updated_at": attempts[-1].created_at.isoformat() if attempts[-1].created_at else "",
            "attempts": [a.raw_result for a in attempts],
        }
    except Exception:
        logger.exception(f"[ProcessingFlow] Failed to read processed data from DB for {session_id}")
        return None


async def _write_processed(session_id: str, pir: str, raw_result: str, uow=None) -> None:
    """Append a processing agent result to the processing_attempts table.

    Does NOT commit — the caller (dialogue endpoint) is responsible for committing
    the full transaction after saving session state.
    """
    if uow is None:
        raise RuntimeError(f"[ProcessingFlow] UoW required to persist processed data for {session_id}")
    await uow.processing_attempts.append(session_id, pir, raw_result)
    logger.info(f"[ProcessingFlow] Appended processing attempt to DB for {session_id}")
    logger.info(f"[ProcessingFlow] Wrote processed.json for {session_id}")


class ProcessingState(str, Enum):
    PROCESSING = "processing"
    REVIEWING = "reviewing"
    COMPLETE = "complete"


class ProcessingFlow(BasePhaseFlow):
    """State machine for the Processing phase.

    States: PROCESSING -> REVIEWING -> COMPLETE

    Each state has a dedicated handler. All state transitions happen in these handlers.
    """

    def __init__(
        self,
        session_id: str | None = None,
        pir: str = "",
        direction_context=None,
        research_logger=None,
    ):
        super().__init__(session_id, research_logger)
        self.pir = pir
        self.direction_context = direction_context
        self.state = ProcessingState.PROCESSING
        # TODO: DB migration — pending_reasoning_log written to DB on approval.
        # Replace with a ReasoningLog table insert when DB is in place.
        self.pending_reasoning_log: ReasoningLog | None = None

    # TODO: DB migration — to_dict and from_dict replace with SQLAlchemy model read/write.
    # ProcessingFlow state (pir, state, direction_context) becomes columns in a sessions table.
    def to_dict(self) -> dict:
        """Serialize session state to a plain dict for JSON persistence."""
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "pir": self.pir,
            "direction_context": (
                self.direction_context.model_dump() if self.direction_context else None
            ),
            "pending_reasoning_log": (
                self.pending_reasoning_log.model_dump()
                if self.pending_reasoning_log
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict, research_logger=None) -> "ProcessingFlow":
        """Reconstruct a ProcessingFlow from a persisted dict."""
        flow = cls(
            session_id=data["session_id"],
            pir=data["pir"],
            direction_context=(
                DialogueContext.model_validate(data["direction_context"])
                if data.get("direction_context")
                else None
            ),
            research_logger=research_logger,
        )
        flow.state = ProcessingState(data["state"])
        flow.pending_reasoning_log = (
            ReasoningLog.model_validate(data["pending_reasoning_log"])
            if data.get("pending_reasoning_log")
            else None
        )
        return flow

    async def initialize(
        self,
        processing_service,
        orchestrator=None,
        reviewer=None,
        uow=None,
    ) -> DialogueResponse:
        """Start processing: read collected data, run agent, write to DB, go to REVIEWING."""
        if not self.session_id:
            return DialogueResponse(action=DialogueAction.ERROR, content="No session ID set.")

        collected = await _read_collected(self.session_id, uow=uow)
        if not collected:
            return DialogueResponse(
                action=DialogueAction.ERROR,
                content="No collected data found. Complete the Collection phase first.",
            )

        raw_collected = "\n\n---\n\n".join(collected.get("attempts", []))

        previous = await _read_processed(self.session_id, uow=uow)
        previous_result = (
            previous["attempts"][-1]
            if previous and previous.get("attempts")
            else None
        )

        try:
            if orchestrator and reviewer:
                raw_result = await orchestrator.process_and_review(
                    collected_data=raw_collected,
                    pir=self.pir,
                    processing_service=processing_service,
                    reviewer=reviewer,
                    session_id=self.session_id,
                    previous_result=previous_result,
                )
                retry_count = len(orchestrator.attempts) - 1
                self.pending_reasoning_log = ReasoningLog(
                    session_id=self.session_id,
                    phase=_PHASE_PROCESSING,
                    model_used=orchestrator.generator_model,
                    dialogue_turns=[],
                    generated_content_attempts=orchestrator.attempts,
                    review_reasoning=orchestrator.review_results,
                    retry_explanation=orchestrator.retry_explanations,
                    final_approved_content=None,
                    timestamps={"processing_performed": datetime.now().isoformat()},
                    retry_triggered=retry_count > 0,
                    retry_count=retry_count,
                )
            else:
                raw_result = await processing_service.process(
                    collected_data=raw_collected,
                    pir=self.pir,
                )
        except Exception:
            logger.error(f"[ProcessingFlow] Processing failed for {self.session_id}", exc_info=True)
            return DialogueResponse(action=DialogueAction.ERROR, content="Processing failed")

        self.state = ProcessingState.REVIEWING
        logger.info(f"[Session {self.session_id}] State: PROCESSING -> REVIEWING")
        await _write_processed(self.session_id, self.pir, raw_result, uow=uow)

        response = DialogueResponse(action=DialogueAction.SHOW_PROCESSING, content=raw_result)

        if orchestrator and orchestrator.review_results:
            response.review_activity = [
                PhaseReviewItem(
                    phase="processing",
                    attempt=i + 1,
                    reviewer_approved=review["approved"],
                    reviewer_suggestions=review.get("suggestions"),
                    sources_used=[],
                    generated_content=(
                        str(orchestrator.attempts[i])
                        if i < len(orchestrator.attempts)
                        else None
                    ),
                )
                for i, review in enumerate(orchestrator.review_results)
            ]

        return response

    async def process_user_message(
        self,
        user_message,
        processing_service,
        approved=None,
        uow=None,
    ) -> DialogueResponse:
        """Route the incoming message to the correct state handler."""
        if self.state == ProcessingState.REVIEWING:
            return await self.handle_reviewing(user_message, processing_service, approved, uow=uow)
        else:
            return DialogueResponse(action=DialogueAction.COMPLETE, content="Processing phase completed")

    async def handle_reviewing(
        self,
        user_message,
        processing_service,
        approved,
        uow=None,
    ) -> DialogueResponse:
        """
        State handler for reviewing phase.
        Possible outcomes:
          - Approve (approved=True)  → COMPLETE, write reasoning log
          - Modify (approved=False)  → Re-run with analyst feedback, self-loop
        """
        if approved:
            self._log_user_action(
                action="approve", phase=self.state.value, modifications=None
            )
            if self.pending_reasoning_log and self.research_logger:
                processed = await _read_processed(self.session_id, uow=uow)
                self.pending_reasoning_log.final_approved_content = (
                    json.dumps(processed) if processed else ""
                )
                self.pending_reasoning_log.timestamps["processing_approved"] = (
                    datetime.now().isoformat()
                )
                self.research_logger.write_reasoning_log(self.pending_reasoning_log)
            self.state = ProcessingState.COMPLETE
            logger.info(f"[Session {self.session_id}] State: REVIEWING -> COMPLETE. Processing phase finished")
            return DialogueResponse(action=DialogueAction.COMPLETE, content="Processing phase complete")

        else:
            self._log_user_action(
                action="modify", phase=self.state.value, modifications=user_message
            )
            processed = await _read_processed(self.session_id, uow=uow)
            last_result = (
                processed["attempts"][-1]
                if processed and processed.get("attempts")
                else ""
            )
            try:
                modified = await processing_service.modify_processing(last_result, user_message)
            except Exception:
                logger.error(f"[ProcessingFlow] Failed to modify processing result for {self.session_id}", exc_info=True)
                return DialogueResponse(action=DialogueAction.ERROR, content="Failed to modify processing result")
            await _write_processed(self.session_id, self.pir, modified, uow=uow)
            return DialogueResponse(action=DialogueAction.SHOW_PROCESSING, content=modified)
