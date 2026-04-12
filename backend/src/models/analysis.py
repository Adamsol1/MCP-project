"""Models for analysis-phase processing results, drafts, and council output."""

from pydantic import BaseModel, Field

from src.models.confidence import FindingConfidence, PerspectiveAssertion


class FindingModel(BaseModel):
    """A structured finding extracted during the processing phase."""

    id: str = Field(..., description="Unique finding identifier")
    title: str = Field(..., description="Short finding title")
    finding: str = Field(..., description="Detailed finding statement")
    evidence_summary: str = Field(..., description="Concise evidence summary")
    source: str = Field(..., description="Source category for the finding")
    confidence: int = Field(
        ..., ge=0, le=100, description="AI-generated confidence (legacy, 0–100)"
    )
    relevant_to: list[str] = Field(
        default_factory=list, description="Related PIR identifiers"
    )
    supporting_data: dict[str, list[str]] = Field(
        default_factory=dict, description="Structured support data for downstream use"
    )
    why_it_matters: str = Field(..., description="Analytical significance of finding")
    uncertainties: list[str] = Field(
        default_factory=list, description="Known uncertainties or unresolved questions"
    )
    computed_confidence: FindingConfidence | None = Field(
        default=None,
        description="Algorithm-computed confidence breakdown (None until enrichment pass)",
    )


class ProcessingResult(BaseModel):
    """Structured result from the processing phase."""

    findings: list[FindingModel] = Field(
        default_factory=list, description="Processed findings for analysis"
    )
    gaps: list[str] = Field(
        default_factory=list, description="Outstanding intelligence gaps"
    )


class AnalysisDraft(BaseModel):
    """Draft analysis produced from processed findings."""

    summary: str = Field(..., description="Short analytical summary")
    key_judgments: list[str] = Field(
        default_factory=list, description="Primary analytical judgments"
    )
    per_perspective_implications: dict[str, list[PerspectiveAssertion]] = Field(
        default_factory=dict,
        description="Implications grouped by analytical perspective, with evidence trace",
    )
    recommended_actions: list[str] = Field(
        default_factory=list, description="Recommended follow-up actions"
    )
    information_gaps: list[str] = Field(
        default_factory=list, description="Remaining information gaps"
    )


class CouncilTranscriptEntry(BaseModel):
    """A single council debate response."""

    round: int = Field(..., description="Round number")
    participant: str = Field(..., description="User-visible participant label")
    response: str = Field(..., description="Debate response text")
    timestamp: str = Field(..., description="ISO timestamp")


class CouncilRuntimeProfile(BaseModel):
    """Fixed application runtime profile for analysis-stage council runs."""

    adapter: str = Field(..., description="Council adapter/runtime family")
    model: str = Field(..., description="Default model identifier")
    mode: str = Field(..., description="Deliberation mode")
    rounds: int = Field(..., description="Configured round count")
    timeout_per_round_seconds: int = Field(
        ..., description="Configured timeout per round in seconds"
    )
    vote_retry_enabled: bool = Field(
        ..., description="Whether vote retry prompting is enabled"
    )
    vote_retry_attempts: int = Field(
        ..., description="Configured vote retry attempts"
    )
    working_directory: str = Field(..., description="Working directory for council")
    file_tree_injection_enabled: bool = Field(
        ..., description="Whether file-tree injection is enabled"
    )
    decision_graph_enabled: bool = Field(
        ..., description="Whether decision-graph context is enabled"
    )


class CouncilRunSettings(BaseModel):
    """User-configurable runtime overrides for analysis-stage council runs."""

    mode: str = Field(default="conference", pattern="^(conference|quick)$")
    rounds: int = Field(default=2, ge=1, le=5)
    timeout_seconds: int = Field(default=180, ge=30, le=900)
    vote_retry_enabled: bool = Field(default=True)
    vote_retry_attempts: int = Field(default=1, ge=0, le=3)


class CouncilNote(BaseModel):
    """Stable backend response model for analysis-stage council output."""

    status: str = Field(..., description="Council run status")
    question: str = Field(..., description="Debate question posed to the council")
    participants: list[str] = Field(
        default_factory=list, description="User-visible participant labels"
    )
    rounds_completed: int = Field(..., description="Number of rounds completed")
    summary: str = Field(..., description="Council summary / consensus text")
    key_agreements: list[str] = Field(
        default_factory=list, description="Key areas of agreement"
    )
    key_disagreements: list[str] = Field(
        default_factory=list, description="Key areas of disagreement"
    )
    final_recommendation: str = Field(
        ..., description="Final recommendation from the council"
    )
    full_debate: list[CouncilTranscriptEntry] = Field(
        default_factory=list, description="Structured debate transcript"
    )
    transcript_path: str | None = Field(
        default=None, description="Path to transcript file if available"
    )


class AnalysisSessionState(BaseModel):
    """Persisted analysis-stage state for one session."""

    session_id: str = Field(..., description="Session identifier")
    processing_result: ProcessingResult | None = Field(
        default=None, description="Persisted processing result"
    )
    analysis_draft: AnalysisDraft | None = Field(
        default=None, description="Persisted analysis draft"
    )
    latest_council_note: CouncilNote | None = Field(
        default=None, description="Most recent council note"
    )
