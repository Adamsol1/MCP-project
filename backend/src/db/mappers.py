"""SessionMapper — converts between IntelligenceSession / flow objects and DB rows.

Uses the existing to_dict() / from_dict() methods on the state machines as an
intermediate representation, keeping state machine code untouched.
"""

import json
from datetime import UTC, datetime

from src.db.models.session_tables import SessionTable


def session_to_row(session) -> SessionTable:
    """Map an IntelligenceSession to a SessionTable row.

    Args:
        session: An IntelligenceSession instance (imported lazily to avoid circles).
    """
    direction_data = session.direction_flow.to_dict()
    collection_data = (
        session.collection_flow.to_dict() if session.collection_flow else None
    )
    processing_data = (
        session.processing_flow.to_dict() if session.processing_flow else None
    )
    analysis_data = (
        session.analysis_flow.to_dict()
        if getattr(session, "analysis_flow", None)
        else None
    )
    council_data = (
        session.council_flow.to_dict()
        if getattr(session, "council_flow", None)
        else None
    )

    row = SessionTable(
        id=session.session_id,
        updated_at=datetime.now(UTC),
        # Direction flow
        direction_state=direction_data["state"],
        direction_context=json.dumps(direction_data["context"]),
        question_count=direction_data.get("question_count", 0),
        current_pir=direction_data.get("current_pir"),
        pending_reasoning_log_direction=(
            json.dumps(direction_data["pending_reasoning_log"])
            if direction_data.get("pending_reasoning_log")
            else None
        ),
    )

    # Collection flow
    if collection_data:
        row.collection_state = collection_data["state"]
        row.pir = collection_data.get("pir", "")
        row.collection_plan = collection_data.get("collection_plan")
        row.selected_sources = json.dumps(collection_data.get("selected_sources", []))
        row.gather_more_feedback = collection_data.get("gather_more_feedback")
        row.pending_reasoning_log_collection = (
            json.dumps(collection_data["pending_reasoning_log"])
            if collection_data.get("pending_reasoning_log")
            else None
        )

    # Processing flow
    if processing_data:
        row.processing_state = processing_data["state"]
        if not row.pir:
            row.pir = processing_data.get("pir", "")
        row.pending_reasoning_log_processing = (
            json.dumps(processing_data["pending_reasoning_log"])
            if processing_data.get("pending_reasoning_log")
            else None
        )

    # Analysis flow
    if analysis_data:
        row.analysis_state = analysis_data["state"]
        if not row.pir:
            row.pir = analysis_data.get("pir", "")
        row.analysis_result = (
            json.dumps(analysis_data["analysis_result"])
            if analysis_data.get("analysis_result")
            else None
        )

    # Council flow
    if council_data:
        row.council_state = council_data["state"]
        row.latest_council_note = (
            json.dumps(council_data["latest_council_note"])
            if council_data.get("latest_council_note")
            else None
        )

    return row


def row_to_session(row: SessionTable, research_logger):
    """Reconstruct an IntelligenceSession from a SessionTable row.

    Imports are done inside the function to avoid circular dependencies
    between the db package and the services package.
    """
    # Avoid circular import — import here
    from src.api.dialogue import IntelligenceSession
    from src.services.state_machines.analysis_flow import AnalysisFlow
    from src.services.state_machines.collection_flow import CollectionFlow
    from src.services.state_machines.council_flow import CouncilFlow
    from src.services.state_machines.direction_flow import DirectionFlow
    from src.services.state_machines.processing_flow import ProcessingFlow

    # Reconstruct direction flow dict
    direction_data = {
        "session_id": row.id,
        "state": row.direction_state,
        "context": json.loads(row.direction_context) if row.direction_context else {},
        "question_count": row.question_count,
        "current_pir": row.current_pir,
        "pending_reasoning_log": (
            json.loads(row.pending_reasoning_log_direction)
            if row.pending_reasoning_log_direction
            else None
        ),
    }

    # Reconstruct collection flow dict
    collection_data = None
    if row.collection_state:
        collection_data = {
            "session_id": row.id,
            "state": row.collection_state,
            "pir": row.pir or "",
            "collection_plan": row.collection_plan,
            "selected_sources": json.loads(row.selected_sources)
            if row.selected_sources
            else [],
            "gather_more_feedback": row.gather_more_feedback,
            "direction_context": json.loads(row.direction_context)
            if row.direction_context
            else None,
            "pending_reasoning_log": (
                json.loads(row.pending_reasoning_log_collection)
                if row.pending_reasoning_log_collection
                else None
            ),
        }

    # Reconstruct processing flow dict
    processing_data = None
    if row.processing_state:
        processing_data = {
            "session_id": row.id,
            "state": row.processing_state,
            "pir": row.pir or "",
            "direction_context": json.loads(row.direction_context)
            if row.direction_context
            else None,
            "pending_reasoning_log": (
                json.loads(row.pending_reasoning_log_processing)
                if row.pending_reasoning_log_processing
                else None
            ),
        }

    # Reconstruct analysis flow dict
    analysis_data = None
    if row.analysis_state:
        analysis_data = {
            "session_id": row.id,
            "state": row.analysis_state,
            "pir": row.pir or "",
            "analysis_result": (
                json.loads(row.analysis_result) if row.analysis_result else None
            ),
        }

    # Reconstruct council flow dict
    council_data = None
    if row.council_state:
        council_data = {
            "session_id": row.id,
            "state": row.council_state,
            "latest_council_note": (
                json.loads(row.latest_council_note) if row.latest_council_note else None
            ),
        }

    # Build IntelligenceSession
    session = IntelligenceSession.__new__(IntelligenceSession)
    session.session_id = row.id
    session.research_logger = research_logger
    session.direction_flow = DirectionFlow.from_dict(
        direction_data, research_logger=research_logger
    )
    session.collection_flow = (
        CollectionFlow.from_dict(collection_data, research_logger=research_logger)
        if collection_data
        else None
    )
    session.processing_flow = (
        ProcessingFlow.from_dict(processing_data, research_logger=research_logger)
        if processing_data
        else None
    )
    session.analysis_flow = (
        AnalysisFlow.from_dict(analysis_data, research_logger=research_logger)
        if analysis_data
        else None
    )
    session.council_flow = (
        CouncilFlow.from_dict(council_data, research_logger=research_logger)
        if council_data
        else None
    )
    return session
