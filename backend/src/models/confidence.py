"""Pydantic models for confidence scoring: collection coverage and assertion-level."""

from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared tier enum
# ---------------------------------------------------------------------------


class ConfidenceTier(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    ASSESSED = "assessed"


# ---------------------------------------------------------------------------
# Collection Coverage (Layer 0 — existing)
# ---------------------------------------------------------------------------


class CoverageFindingRef(BaseModel):
    """Lightweight reference to a finding that contributed to a PIR's coverage score."""

    id: str
    title: str
    source: str


class PirCoverageScore(BaseModel):
    pir_index: int = Field(..., description="Zero-based PIR index")
    pir_question: str = Field(..., description="The PIR question text")
    priority: str = Field(..., description="high / medium / low")
    tier: ConfidenceTier = Field(..., description="Coverage confidence tier")
    score: float = Field(..., ge=0.0, le=1.0, description="Raw 0-1 float (internal)")
    finding_count: int = Field(..., description="Number of findings mapped to this PIR")
    source_types: list[str] = Field(
        default_factory=list, description="Distinct source types contributing"
    )
    has_gap_flag: bool = Field(
        ..., description="True if gaps mention this PIR's topic"
    )
    rationale: str = Field(..., description="Human-readable explanation of the score")
    findings: list[CoverageFindingRef] = Field(
        default_factory=list,
        description="The actual findings that mapped to this PIR",
    )


class CollectionCoverageResult(BaseModel):
    per_pir: list[PirCoverageScore] = Field(default_factory=list)
    aggregate_tier: ConfidenceTier = Field(
        ..., description="Overall collection coverage tier"
    )
    aggregate_score: float = Field(..., ge=0.0, le=1.0)
    summary: str = Field(..., description="One-sentence summary for the analyst")


# ---------------------------------------------------------------------------
# Confidence Algorithm (Layer 1) — dataclass for internal use
# ---------------------------------------------------------------------------


@dataclass
class ConfidenceBreakdown:
    """Internal result from compute_confidence. Not serialised directly."""

    authority: float
    corroboration: float
    independence: float
    raw_score: float
    tier: str  # ConfidenceTier value
    source_types: list[str] = field(default_factory=list)
    circular_flag: bool = False


# ---------------------------------------------------------------------------
# Finding-Level Confidence (Layer 2)
# ---------------------------------------------------------------------------


class FindingConfidence(BaseModel):
    """Algorithm-computed confidence for a single finding."""

    tier: ConfidenceTier
    score: float = Field(..., ge=0.0, le=1.0)
    authority: float = Field(..., ge=0.0, le=1.0)
    corroboration: float = Field(..., ge=0.0, le=1.0)
    independence: float = Field(..., ge=0.0, le=1.0)
    circular_flag: bool = False
    source_types: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Assertion-Level Confidence (Layer 3)
# ---------------------------------------------------------------------------


class AssertionConfidence(BaseModel):
    """Computed confidence for a single per-perspective assertion."""

    tier: ConfidenceTier
    score: float = Field(..., ge=0.0, le=1.0)
    authority: float = Field(..., ge=0.0, le=1.0)
    corroboration: float = Field(..., ge=0.0, le=1.0)
    independence: float = Field(..., ge=0.0, le=1.0)
    circular_flag: bool = False


class PerspectiveAssertion(BaseModel):
    """A single per-perspective implication with full evidence trace."""

    assertion: str = Field(..., description="The implication/assertion text")
    supporting_finding_ids: list[str] = Field(
        default_factory=list,
        description="Finding IDs that back this assertion",
    )
    source_types: list[str] = Field(
        default_factory=list,
        description="Distinct source types across supporting findings",
    )
    confidence: AssertionConfidence | None = Field(
        default=None,
        description="Computed confidence (None until enrichment pass)",
    )
