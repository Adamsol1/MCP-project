from __future__ import annotations

import json
import logging
from enum import Enum
from typing import TYPE_CHECKING

from src.models.analysis import CouncilNote, CouncilRunSettings
from src.models.dialogue import DialogueAction, DialogueResponse
from src.services.state_machines.base_phase_flow import BasePhaseFlow

if TYPE_CHECKING:
    from src.services.state_machines.analysis_flow import AnalysisFlow

logger = logging.getLogger("app")


class CouncilState(str, Enum):
    IDLE = "idle"
    COMPLETE = "complete"


class CouncilFlow(BasePhaseFlow):
    def __init__(
        self,
        session_id: str | None = None,
        research_logger=None,
    ):
        super().__init__(session_id, research_logger)
        self.state = CouncilState.IDLE
        self.latest_council_note: dict | None = None

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "latest_council_note": self.latest_council_note,
        }

    @classmethod
    def from_dict(cls, data: dict, research_logger=None) -> CouncilFlow:
        flow = cls(
            session_id=data["session_id"],
            research_logger=research_logger,
        )
        flow.state = CouncilState(data["state"])
        flow.latest_council_note = data.get("latest_council_note")
        return flow

    async def process_user_message(  # type: ignore[override]
        self,
        debate_point: str,
        finding_ids: list[str],
        selected_perspectives: list[str],
        council_service,
        analysis_flow: AnalysisFlow | None = None,
        council_settings: CouncilRunSettings | None = None,
    ) -> DialogueResponse:
        from src.models.analysis import AnalysisDraft, ProcessingResult

        if not analysis_flow or not analysis_flow.analysis_result:
            return DialogueResponse(
                action=DialogueAction.ERROR,
                content="Analysis must be complete before running council.",
            )

        try:
            processing_result = ProcessingResult.model_validate(
                analysis_flow.analysis_result["processing_result"]
            )
            analysis_draft = AnalysisDraft.model_validate(
                analysis_flow.analysis_result["analysis_draft"]
            )
        except Exception:
            logger.error(
                "[CouncilFlow] Failed to load analysis data for session %s",
                self.session_id,
                exc_info=True,
            )
            return DialogueResponse(
                action=DialogueAction.ERROR, content="Failed to load analysis data."
            )

        try:
            council_note: CouncilNote = await council_service.run_council(
                session_id=self.session_id,
                debate_point=debate_point,
                selected_perspectives=selected_perspectives,
                processing_result=processing_result,
                analysis_draft=analysis_draft,
                finding_ids=finding_ids or None,
                council_settings=council_settings,
            )
        except Exception as exc:
            logger.error(
                "[CouncilFlow] Council run failed for session %s: %s",
                self.session_id,
                exc,
                exc_info=True,
            )
            return DialogueResponse(action=DialogueAction.ERROR, content=str(exc))

        self.latest_council_note = council_note.model_dump()
        self.state = CouncilState.COMPLETE
        logger.info("[Session %s] CouncilFlow: -> COMPLETE", self.session_id)

        return DialogueResponse(
            action=DialogueAction.SHOW_COUNCIL,
            content=json.dumps(self.latest_council_note),
        )
