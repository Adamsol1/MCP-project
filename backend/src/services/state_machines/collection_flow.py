import logging
from enum import Enum

from src.models.dialogue import DialogueResponse
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

    async def initialize(self, collection_service) -> DialogueResponse:
        # Generer innsamlingsplan basert på self.pir
        # Sett state til PLAN_CONFIRMING
        # Returner DialogueResponse med action="show_plan"
        ...

    async def process_user_message(self, user_message, collection_service, approved=None) -> DialogueResponse:
        if self.state == CollectionState.PLAN_CONFIRMING:
            
        elif self.state == CollectionState.SOURCE_SELECTING:
            ...
        elif self.state == CollectionState.COLLECTING:
            ...
        elif self.state == CollectionState.REVIEWING:
            ...
        else:
            ...

    async def handle_plan_confirming(self, user_message, collection_service, approved) -> DialogueResponse:
        ...

    async def handle_source_selecting(self, user_message, collection_service) -> DialogueResponse:
        ...

    async def handle_collecting(self, collection_service) -> DialogueResponse:
        ...

    async def handle_reviewing(self, user_message, collection_service, approved) -> DialogueResponse:
        ...
