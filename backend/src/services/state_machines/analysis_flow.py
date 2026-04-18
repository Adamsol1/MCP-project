import json
import logging
from enum import Enum

from src.models.dialogue import DialogueAction, DialogueResponse, PhaseReviewItem
from src.services.confidence.collection_coverage import compute_collection_coverage
from src.services.state_machines.base_phase_flow import BasePhaseFlow

logger = logging.getLogger("app")


class AnalysisState(str, Enum):
    PENDING = "pending"
    COMPLETE = "complete"


class AnalysisFlow(BasePhaseFlow):
    def __init__(
        self,
        session_id: str | None = None,
        pir: str = "",
        research_logger=None,
    ):
        super().__init__(session_id, research_logger)
        self.pir = pir
        self.state = AnalysisState.PENDING
        self.analysis_result: dict | None = None

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "pir": self.pir,
            "analysis_result": self.analysis_result,
        }

    @classmethod
    def from_dict(cls, data: dict, research_logger=None) -> "AnalysisFlow":
        flow = cls(
            session_id=data["session_id"],
            pir=data.get("pir", ""),
            research_logger=research_logger,
        )
        flow.state = AnalysisState(data["state"])
        flow.analysis_result = data.get("analysis_result")
        return flow

    def _extract_pirs(self) -> list[dict]:
        if not self.pir:
            return []
        try:
            pir_data = json.loads(self.pir)
            pirs: list[dict] = pir_data.get("pirs", [])
            return [p for p in pirs if isinstance(p, dict) and "question" in p]
        except (json.JSONDecodeError, AttributeError):
            logger.warning(
                "[AnalysisFlow] Failed to parse PIR JSON for session %s",
                self.session_id,
            )
            return []

    async def initialize(
        self,
        processing_service,
        analysis_service,
        orchestrator=None,
        reviewer=None,
        selected_perspectives: list[str] | None = None,
    ) -> DialogueResponse:
        if not self.session_id:
            return DialogueResponse(
                action=DialogueAction.ERROR, content="No session ID set."
            )

        try:
            processing_result = await processing_service.get_processing_result(
                self.session_id
            )
        except ValueError as exc:
            logger.error(
                "[AnalysisFlow] Failed to load processing result for %s: %s",
                self.session_id,
                exc,
            )
            return DialogueResponse(action=DialogueAction.ERROR, content=str(exc))

        try:
            if orchestrator and reviewer:
                analysis_draft, enriched_result = await orchestrator.analyse_and_review(
                    processing_result=processing_result,
                    analysis_service=analysis_service,
                    reviewer=reviewer,
                    session_id=self.session_id,
                    pir=self.pir,
                    selected_perspectives=selected_perspectives,
                )
            else:
                analysis_draft, enriched_result = await analysis_service.generate_draft(
                    processing_result,
                    selected_perspectives=selected_perspectives,
                )
        except Exception:
            logger.error(
                "[AnalysisFlow] Analysis generation failed for %s",
                self.session_id,
                exc_info=True,
            )
            return DialogueResponse(
                action=DialogueAction.ERROR, content="Analysis generation failed."
            )

        pirs = self._extract_pirs()
        coverage = compute_collection_coverage(
            findings=enriched_result.findings,
            gaps=enriched_result.gaps,
            pirs=pirs,
        )

        result = {
            "processing_result": enriched_result.model_dump(),
            "analysis_draft": analysis_draft.model_dump(),
            "collection_coverage": coverage.model_dump() if coverage else None,
        }

        self.analysis_result = result
        self.state = AnalysisState.COMPLETE
        logger.info("[Session %s] AnalysisFlow: PENDING -> COMPLETE", self.session_id)

        response = DialogueResponse(
            action=DialogueAction.SHOW_ANALYSIS,
            content=json.dumps(result),
        )

        if orchestrator and orchestrator.review_results:
            response.review_activity = [
                PhaseReviewItem(
                    phase="analysis",
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

    async def process_user_message(self, **_kwargs) -> DialogueResponse:
        if self.state == AnalysisState.COMPLETE and self.analysis_result:
            return DialogueResponse(
                action=DialogueAction.SHOW_ANALYSIS,
                content=json.dumps(self.analysis_result),
            )
        return DialogueResponse(
            action=DialogueAction.ERROR, content="Analysis is not ready yet."
        )
