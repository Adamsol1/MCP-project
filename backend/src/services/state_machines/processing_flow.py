"""ProcessingFlow — state machine for the Processing phase.

Reads raw collected data from collected.json, runs the processing agent
(normalize → enrich → correlate → synthesize), writes the result to
processed.json, and presents it for analyst review.

States:
    PROCESSING  — agent has not yet run (waiting for initialize)
    REVIEWING   — analyst is reviewing the processed result
    COMPLETE    — analyst approved, phase done
"""

import json
import logging
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from src.models.dialogue import DialogueContext, DialogueResponse
from src.models.reasoning import ReasoningLog
from src.services.state_machines.base_phase_flow import BasePhaseFlow

logger = logging.getLogger("app")

_SESSIONS_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "sessions"


def _collected_path(session_id: str) -> Path:
    return _SESSIONS_DATA_DIR / session_id / "collected.json"


def _processed_path(session_id: str) -> Path:
    return _SESSIONS_DATA_DIR / session_id / "processed.json"


def _read_collected(session_id: str) -> dict | None:
    path = _collected_path(session_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception(f"[ProcessingFlow] Failed to read collected.json for {session_id}")
        return None


def _read_processed(session_id: str) -> dict | None:
    path = _processed_path(session_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception(f"[ProcessingFlow] Failed to read processed.json for {session_id}")
        return None


def _write_processed(session_id: str, pir: str, raw_result: str) -> None:
    """Append a processing agent result to processed.json."""
    path = _processed_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_processed(session_id)
    now = datetime.now(UTC).isoformat()
    if existing:
        existing["attempts"].append(raw_result)
        existing["updated_at"] = now
    else:
        existing = {
            "session_id": session_id,
            "pir": pir,
            "processed_at": now,
            "updated_at": now,
            "attempts": [raw_result],
        }
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"[ProcessingFlow] Wrote processed.json for {session_id}")


class ProcessingState(str, Enum):
    PROCESSING = "processing"
    REVIEWING = "reviewing"
    COMPLETE = "complete"


class ProcessingFlow(BasePhaseFlow):

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
        self.pending_reasoning_log: ReasoningLog | None = None

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

    async def initialize(self, processing_service) -> DialogueResponse:
        """Start processing: read collected data, run agent, write processed.json, go to REVIEWING."""
        collected = _read_collected(self.session_id)
        if not collected:
            return DialogueResponse(
                action="error",
                content="No collected data found. Complete the Collection phase first.",
            )

        raw_collected = "\n\n---\n\n".join(collected.get("attempts", []))

        try:
            raw_result = await processing_service.process(
                collected_data=raw_collected,
                pir=self.pir,
            )
        except Exception as e:
            logger.error(f"[ProcessingFlow] Processing failed for {self.session_id}: {e}")
            return DialogueResponse(action="error", content=f"Processing failed: {e}")

        self.state = ProcessingState.REVIEWING
        _write_processed(self.session_id, self.pir, raw_result)

        return DialogueResponse(action="show_processing", content=raw_result)

    async def process_user_message(
        self,
        user_message,
        processing_service,
        approved=None,
    ) -> DialogueResponse:
        if self.state == ProcessingState.REVIEWING:
            return await self.handle_reviewing(user_message, processing_service, approved)
        else:
            return DialogueResponse(action="complete", content="Processing phase completed")

    async def handle_reviewing(
        self,
        user_message,
        processing_service,
        approved,
    ) -> DialogueResponse:
        """
        State handler for reviewing phase.
        Possible outcomes:
          - Approve (approved=True)  → COMPLETE, write reasoning log
          - Modify (approved=False)  → Re-run with analyst feedback, self-loop
        """
        if approved:
            self._log_user_action(
                action="approve", phase="reviewing", modifications=None
            )
            if self.pending_reasoning_log and self.research_logger:
                processed = _read_processed(self.session_id)
                self.pending_reasoning_log.final_approved_content = (
                    json.dumps(processed) if processed else ""
                )
                self.pending_reasoning_log.timestamps["processing_approved"] = (
                    datetime.now().isoformat()
                )
                self.research_logger.write_reasoning_log(self.pending_reasoning_log)
            self.state = ProcessingState.COMPLETE
            return DialogueResponse(action="complete", content="Processing phase complete")

        else:
            self._log_user_action(
                action="modify", phase="reviewing", modifications=user_message
            )
            processed = _read_processed(self.session_id)
            last_result = (
                processed["attempts"][-1]
                if processed and processed.get("attempts")
                else ""
            )
            modified = await processing_service.modify_processing(last_result, user_message)
            _write_processed(self.session_id, self.pir, modified)
            return DialogueResponse(action="show_processing", content=modified)
