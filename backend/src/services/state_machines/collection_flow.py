import json
import logging
from datetime import UTC, datetime
from enum import Enum

from src.models.dialogue import DialogueAction, DialogueContext, DialogueResponse
from src.models.reasoning import ReasoningLog
from src.services.collection_service import CollectionService
from src.services.state_machines.base_phase_flow import BasePhaseFlow

logger = logging.getLogger("app")


async def _read_collected(session_id: str, uow=None) -> dict | None:
    """Read collected data from DB via UoW."""
    if uow is None:
        raise RuntimeError(f"[CollectionFlow] UoW required to read collected data for {session_id}")
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
        logger.exception(f"[CollectionFlow] Failed to read collected data from DB for {session_id}")
        return None


async def _write_collected(session_id: str, pir: str, raw_data: str, uow=None) -> None:
    """Append a raw agent response to the collection_attempts table.

    Does NOT commit — the caller (dialogue endpoint) is responsible for committing
    the full transaction after saving session state.
    """
    if uow is None:
        raise RuntimeError(f"[CollectionFlow] UoW required to persist collected data for {session_id}")
    await uow.collection_attempts.append(session_id, pir, raw_data)
    logger.info(f"[CollectionFlow] Appended collection attempt to DB for {session_id}")


class CollectionState(str, Enum):
    PLANNING = "planning"
    PLAN_CONFIRMING = "plan_confirming"
    COLLECTING = "collecting"
    REVIEWING = "reviewing"
    COMPLETE = "complete"


class CollectionFlow(BasePhaseFlow):

    def __init__(self, session_id: str | None = None, pir: str = "", direction_context=None, research_logger=None):
        super().__init__(session_id, research_logger)
        self.pir = pir
        self.direction_context = direction_context
        self.state = CollectionState.PLANNING
        self.collection_plan: str | None = None
        self.selected_sources: list[str] = []
        # TODO: DB migration — pending_reasoning_log written to disk on approval.
        # Replace with a ReasoningLog table insert when DB is in place.
        self.pending_reasoning_log: ReasoningLog | None = None
        self.gather_more_feedback: str | None = None

    # TODO: DB migration — to_dict and from_dict replace with SQLAlchemy model read/write.
    # CollectionFlow state (pir, plan, state, sources) becomes columns in a sessions table.
    def to_dict(self) -> dict:
        """Serialize session state to a plain dict for JSON persistence.
        Note: research_logger is excluded — it is reconstructed on load.
        Collected data lives in data/sessions/{session_id}/collected.json — not here."""
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "pir": self.pir,
            "collection_plan": self.collection_plan,
            "selected_sources": self.selected_sources,
            "gather_more_feedback": self.gather_more_feedback,
            "direction_context": self.direction_context.model_dump() if self.direction_context else None,
            "pending_reasoning_log": (
                self.pending_reasoning_log.model_dump() if self.pending_reasoning_log else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict, research_logger=None) -> "CollectionFlow":
        """Reconstruct a CollectionFlow from a persisted dict.
        Called when a session is loaded from disk after a server restart."""
        flow = cls(
            session_id=data["session_id"],
            pir=data["pir"],
            direction_context=DialogueContext.model_validate(data["direction_context"]) if data.get("direction_context") else None,
            research_logger=research_logger,
        )
        flow.state = CollectionState(data["state"])
        flow.collection_plan = data["collection_plan"]
        flow.selected_sources = data["selected_sources"]
        flow.gather_more_feedback = data.get("gather_more_feedback")
        flow.pending_reasoning_log = (
            ReasoningLog.model_validate(data["pending_reasoning_log"])
            if data.get("pending_reasoning_log")
            else None
        )
        return flow

    async def initialize(self, collection_service, uow=None) -> DialogueResponse:
        # Generate collection plan based on self.pir
        # Set state to PLAN_CONFIRMING
        # Return DialogueResponse with action="show_plan"
        try:
            self.collection_plan = await collection_service.generate_collection_plan(self.pir)
        except Exception as e:
            logger.error(f"[Session {self.session_id}] Failed to generate collection plan: {e}")
            return DialogueResponse(action=DialogueAction.ERROR, content="Failed to generate collection plan")

        self.state = CollectionState.PLAN_CONFIRMING
        return DialogueResponse(action=DialogueAction.SHOW_PLAN, content=self.collection_plan or "")

    async def process_user_message(self, user_message, collection_service, approved=None, selected_sources: list[str] | None = None, orchestrator=None, reviewer=None, gather_more: bool = False, uow=None) -> DialogueResponse:
        #PLAN PHASE
        if self.state == CollectionState.PLAN_CONFIRMING:
            return await self.handle_plan_confirming(user_message, collection_service, approved, selected_sources)
        #COLLECTING
        elif self.state == CollectionState.COLLECTING:
            return await self.handle_collecting(collection_service, orchestrator, reviewer, uow=uow)
        #REVIEWING
        elif self.state == CollectionState.REVIEWING:
            return await self.handle_reviewing(user_message, collection_service, approved, gather_more, selected_sources, uow=uow)
        #COMPLETE
        else:
            return DialogueResponse(action=DialogueAction.COMPLETE, content="Collection phase completed")

    async def handle_plan_confirming(self, user_message, collection_service, approved, selected_sources: list[str] | None = None) -> DialogueResponse:
        """
        State handler for plan confirming phase.
        Frontend should send boolean with user input, which decides next action.
        On approve, selected_sources must be provided — source selection happens locally on the frontend.
        Possible outcomes:
            - Approve (approved=True) -> State change: PLAN_CONFIRMING -> COLLECTING
            - Reject (approved=False) -> Regenerate plan with user message. Self loop (stay in PLAN_CONFIRMING)
        """
        dialogue_response = DialogueResponse()

        if approved:
            self._log_user_action(action="approve", phase="handle_plan_confirming", modifications=None, perspectives=None)

            self.selected_sources = selected_sources or []
            self.state = CollectionState.COLLECTING

            dialogue_response.action = DialogueAction.START_COLLECTING
            dialogue_response.content = json.dumps(self.selected_sources)

            return dialogue_response

        else:
            self._log_user_action(action="reject", phase="handle_plan_confirming", modifications=user_message, perspectives=None)

            self.collection_plan = await collection_service.generate_collection_plan(self.pir, user_message)

            dialogue_response.action = DialogueAction.SHOW_PLAN
            dialogue_response.content = self.collection_plan

            return dialogue_response








    async def handle_collecting(
        self,
        collection_service,
        orchestrator=None,
        reviewer=None,
        uow=None,
    ) -> DialogueResponse:
        timeframe = self.direction_context.timeframe if self.direction_context else ""
        perspectives = (
            [p.value for p in self.direction_context.perspectives]
            if self.direction_context else []
        )
        feedback = self.gather_more_feedback
        self.gather_more_feedback = None  # consume once
        try:
            if orchestrator and reviewer:
                collection_summary = await orchestrator.collect_and_review(
                    sources=self.selected_sources,
                    pir=self.pir,
                    plan=self.collection_plan,
                    collection_service=collection_service,
                    reviewer=reviewer,
                    session_id=self.session_id,
                    direction_context=self.direction_context,
                    timeframe=timeframe,
                    perspectives=perspectives,
                    feedback=feedback,
                )
            else:
                collection_summary = await collection_service.collect(
                    self.selected_sources,
                    self.pir,
                    self.collection_plan,
                    timeframe=timeframe,
                    perspectives=perspectives,
                )
        except Exception as e:
            logger.error(f"[Session {self.session_id}] Collection failed: {e}")
            self.state = CollectionState.PLAN_CONFIRMING
            return DialogueResponse(action=DialogueAction.ERROR, content="Collection failed")

        if orchestrator:
            retry_count = len(orchestrator.attempts) - 1
            self.pending_reasoning_log = ReasoningLog(
                session_id=self.session_id,
                phase="collection",
                model_used=orchestrator.generator_model,
                dialogue_turns=[],
                generated_content_attempts=orchestrator.attempts,
                review_reasoning=orchestrator.review_results,
                retry_explanation=orchestrator.retry_explanations,
                final_approved_content=None,
                timestamps={"collection performed": datetime.now().isoformat()},
                retry_triggered=retry_count > 0,
                retry_count=retry_count,
            )

        self.state = CollectionState.REVIEWING
        await _write_collected(self.session_id, self.pir, collection_summary, uow=uow)

        display_payload = CollectionService.parse_collected_data(collection_summary)

        if orchestrator and orchestrator.review_results:
            display_payload["activity_summary"] = [
                {
                    "attempt": i + 1,
                    "collector_sources": self.selected_sources,
                    "reviewer_approved": review["approved"],
                    "reviewer_suggestions": review.get("suggestions"),
                }
                for i, review in enumerate(orchestrator.review_results)
            ]

        return DialogueResponse(action=DialogueAction.SHOW_COLLECTION, content=json.dumps(display_payload, ensure_ascii=False))



    async def handle_reviewing(self, user_message, collection_service, approved, gather_more: bool = False, selected_sources: list[str] | None = None, uow=None) -> DialogueResponse:
        """
        State handler for reviewing phase.
        Possible outcomes:
          - Approve (approved=True) -> REVIEWING -> COMPLETE
          - Modify (approved=False, gather_more=False) -> Trim/rewrite summary with modifications, self-loop
          - Gather More (gather_more=True) -> COLLECTING with new selected_sources (source selection handled on frontend)
        """
        if approved:
            self._log_user_action(action="approve", phase="reviewing", modifications=None, perspectives=None)
            if self.pending_reasoning_log and self.research_logger:
                collected = await _read_collected(self.session_id, uow=uow)
                self.pending_reasoning_log.final_approved_content = json.dumps(collected) if collected else ""
                self.pending_reasoning_log.timestamps["collection_approved"] = datetime.now().isoformat()
                self.research_logger.write_reasoning_log(self.pending_reasoning_log)
            self.state = CollectionState.COMPLETE
            return DialogueResponse(action=DialogueAction.COMPLETE, content="Collection phase complete")

        elif gather_more:
            self._log_user_action(action="gather_more", phase="reviewing", modifications=user_message, perspectives=None)
            if selected_sources:
                self.selected_sources = selected_sources
            # else: keep existing selected_sources from the previous collection run
            self.gather_more_feedback = user_message or None
            self.state = CollectionState.COLLECTING
            return DialogueResponse(action=DialogueAction.START_COLLECTING, content=json.dumps(self.selected_sources))

        else:
            self._log_user_action(action="modify", phase="reviewing", modifications=user_message, perspectives=None)
            collected = await _read_collected(self.session_id, uow=uow)
            raw = collected["attempts"][-1] if collected and collected.get("attempts") else ""
            try:
                modified = await collection_service.modify_summary(raw, user_message)
            except Exception as e:
                logger.error(f"[Session {self.session_id}] Failed to modify summary: {e}")
                return DialogueResponse(action=DialogueAction.ERROR, content="Failed to modify collection summary")
            await _write_collected(self.session_id, self.pir, modified, uow=uow)
            display_payload = CollectionService.parse_collected_data(modified)
            return DialogueResponse(action=DialogueAction.SHOW_COLLECTION, content=json.dumps(display_payload, ensure_ascii=False))


