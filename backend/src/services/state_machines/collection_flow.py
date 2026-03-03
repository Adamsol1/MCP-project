import logging
from datetime import datetime
from enum import Enum

from src.models.dialogue import DialogueResponse
from src.models.reasoning import ReasoningLog
from src.services.state_machines.base_phase_flow import BasePhaseFlow

logger = logging.getLogger("app")


class CollectionState(str, Enum):
    PLANNING = "planning"
    PLAN_CONFIRMING = "plan_confirming"
    SOURCE_SELECTING = "source_selecting"
    COLLECTING = "collecting"
    REVIEWING = "reviewing"
    COMPLETE = "complete"


class CollectionFlow(BasePhaseFlow):

    def __init__(self, session_id: str | None = None, pir: str = "", research_logger=None):
        super().__init__(session_id, research_logger)
        self.pir = pir
        self.state = CollectionState.PLANNING
        self.collection_plan: str | None = None
        self.selected_sources: list[str] = []
        self.collected_data: str | None = None
        self.pending_reasoning_log: ReasoningLog | None = None

    async def initialize(self, collection_service) -> DialogueResponse:
        # Generer innsamlingsplan basert på self.pir
        # Sett state til PLAN_CONFIRMING
        # Returner DialogueResponse med action="show_plan"
        self.collection_plan = await collection_service.generate_collection_plan(self.pir)

        self.state = CollectionState.PLAN_CONFIRMING

        dialogue_response = DialogueResponse(action="show_plan", content=self.collection_plan)

        return dialogue_response

    async def process_user_message(self, user_message, collection_service, approved=None, selected_sources: list[str] | None = None, orchestrator=None, reviewer=None, gather_more: bool = False) -> DialogueResponse:
        #PLAN PHASE
        if self.state == CollectionState.PLAN_CONFIRMING:
            return await self.handle_plan_confirming(user_message, collection_service, approved)
        #SOURCE SELECTING
        elif self.state == CollectionState.SOURCE_SELECTING:
            return await self.handle_source_selecting(selected_sources)
        #COLLECTING
        elif self.state == CollectionState.COLLECTING:
            return await self.handle_collecting(collection_service, orchestrator, reviewer)
        #REVIEWING
        elif self.state == CollectionState.REVIEWING:
            return await self.handle_reviewing(user_message, collection_service, approved, gather_more)
        #COMPLETE
        else:
            return DialogueResponse(action="complete", content="collection phase completed")

    async def handle_plan_confirming(self, user_message, collection_service, approved) -> DialogueResponse:
        """
        State handler for plan confirming phase.
        Frontend should send boolean with user input, which decides next action
        Possible outcomes:
            - Approve (approved=True) -> State change : PLAN_CONFIRMING -> SOURCE SELECTING
            - Reject (approved=False) -> Regenerate plan with user message. Self loop (stay in PLAN_CONFIRMING)
        """
        dialogue_response = DialogueResponse()

        #user approves
        if approved:
            #Log user action
            self._log_user_action(action="approve", phase="handle_plan_confirming", modifications=None, perspectives=None)

            recommended_sources = await collection_service.suggest_sources(self.pir, self.collection_plan)

            #State change PLAN_CONFIRM -> SOURCE_SELECTING
            self.state = CollectionState.SOURCE_SELECTING

            #Inform frontend of action
            dialogue_response.action = "show_suggested_sources"
            dialogue_response.content = recommended_sources

            return dialogue_response

        else:
            #Log user action
            self._log_user_action(action="reject", phase="handle_plan_confirming", modifications=user_message, perspectives=None)

            #Generate new collection plan
            self.collection_plan = await collection_service.generate_collection_plan(self.pir, user_message)

            #Inform frontend of action
            dialogue_response.action = "show_plan"
            dialogue_response.content = self.collection_plan

            return dialogue_response







    async def handle_source_selecting(self, selected_sources: list[str] | None) -> DialogueResponse:
        """
        State handler for source selecting.
        User chooses what sources they want to use for the collection.
        Update the selected sources to flow
        """
        #Check if retrieved sources
        if not selected_sources:
            return DialogueResponse(action="error", content="Du må velge minst én kilde")
        self.selected_sources = selected_sources

        #Change state
        self.state = CollectionState.COLLECTING

        #Return response to frontend
        return DialogueResponse(action="start_collecting", content=selected_sources)




    async def handle_collecting(
            self,
            collection_service,
            orchestrator=None,
            reviewer=None,
                                ) -> DialogueResponse:

    #Collect information

        if orchestrator and reviewer:
            collection_summary = await orchestrator.collect_and_review(
                self.pir,
                self.collection_plan,
                self.selected_sources
            )
        else:
            collection_summary = await collection_service.collect(
                self.selected_sources,
                self.pir,
                self.collection_plan
            )

        if orchestrator:
                retry_count = len(orchestrator.collection_attempts) - 1
                self.pending_reasoning_log = ReasoningLog(
                    session_id=self.session_id,
                    phase="collection",
                    model_used=orchestrator.generator_model,
                    dialogue_turns=[],
                    generated_content_attempts=orchestrator.collection_attempts,
                    review_reasoning=orchestrator.review_results,
                    retry_explanation=orchestrator.retry_explanations,
                    final_approved_content=None,
                    timestamps={"collection performed": datetime.now().isoformat()},
                    retry_triggered=retry_count > 0,
                    retry_count=retry_count,
                )

        self.state = CollectionState.REVIEWING
        self.collected_data = collection_summary
        return DialogueResponse(action="show_collection", content=collection_summary)



    async def handle_reviewing(self, user_message, collection_service, approved, gather_more: bool = False) -> DialogueResponse:
        """
        State handler for reviewing phase.
        Possible outcomes:
          - Approve (approved=True) -> REVIEWING -> COMPLETE
          - Modify (approved=False, gather_more=False) -> Trim/rewrite summary with modifications, self-loop
          - Gather More (gather_more=True) -> Back to SOURCE_SELECTING for new collection
        """
        if approved:
            self._log_user_action(action="approve", phase="reviewing", modifications=None, perspectives=None)
            if self.pending_reasoning_log and self.research_logger:
                self.pending_reasoning_log.final_approved_content = self.collected_data
                self.pending_reasoning_log.timestamps["collection_approved"] = datetime.now().isoformat()
                self.research_logger.write_reasoning_log(self.pending_reasoning_log)
            self.state = CollectionState.COMPLETE
            return DialogueResponse(action="complete", content="Collection phase complete")

        elif gather_more:
            self._log_user_action(action="reject", phase="reviewing", modifications=user_message, perspectives=None)
            self.state = CollectionState.SOURCE_SELECTING
            suggested_sources = await collection_service.suggest_sources(
                self.pir, self.collection_plan, previously_collected=self.collected_data
            )
            return DialogueResponse(action="show_suggested_sources", content=suggested_sources)

        else:
            self._log_user_action(action="modify", phase="reviewing", modifications=user_message, perspectives=None)
            self.collected_data = await collection_service.modify_summary(self.collected_data, user_message)
            return DialogueResponse(action="show_collection", content=self.collected_data)


