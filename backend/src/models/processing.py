"""Models for the Processing phase output.

IntelligenceFinding represents a single processed intelligence observation,
combining normalized, enriched, and correlated data from the collection phase.

ProcessingResult is the top-level output sent to the Analysis phase.
"""

from pydantic import BaseModel, Field

from src.models.enums import DataSource


class IntelligenceFinding(BaseModel):
    """A single processed intelligence observation.

    Represents one meaningful thing learned during processing —
    after normalization, enrichment, and correlation. This is the
    unit of intelligence passed to the Analysis phase.
    """

    finding: str = Field(..., description="Plain-text description of what was found")

    source: DataSource = Field(..., description="Primary source this finding came from")

    confidence: int = Field(..., ge=0, le=100, description="Confidence score 0-100")

    relevant_to: list[str] = Field(
        default_factory=list,
        description="PIR IDs this finding is relevant to (e.g. ['PIR-1', 'PIR-2'])",
    )

    supporting_data: dict = Field(
        default_factory=dict,
        description=(
            "Curated evidence supporting this finding. "
            "For IoCs: ips, domains, attack_ids, first_seen, linked_actors. "
            "For geopolitical: kb_references, related_events, context snippets."
        ),
    )


class ProcessingResult(BaseModel):
    """Output of the Processing phase, sent as input to the Analysis phase.

    Contains all processed intelligence findings and identified gaps.
    Gaps are as analytically important as findings — they show where
    the collection did not produce sufficient data to answer PIRs.
    """

    findings: list[IntelligenceFinding] = Field(
        default_factory=list,
        description="All processed intelligence findings",
    )

    gaps: list[str] = Field(
        default_factory=list,
        description=(
            "Topics or PIRs where insufficient data was found. "
            "Each gap is a plain-text description of what is missing."
        ),
    )
