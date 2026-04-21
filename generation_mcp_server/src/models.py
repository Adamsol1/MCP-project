from pydantic import BaseModel, field_validator
from typing import Literal

class Citation(BaseModel):
  """
  Represents the bibliographic information for a source, following APA7th format.
  All fields are required and must be strings.
  """
  author: str
  year: str
  title: str
  publisher: str

class Source(BaseModel):
  id: str # e.g., "geopolitical/norway_russia" — unique identifier for the source
  ref: str # e.g., "[1]" — this is what gets cited in the claim text and links to the Citation
  source_type: Literal["kb", "doc", "data"] # e.g., "kb", "doc", "data" — this drives the UI badge and is a Literal with limited valid values
  citation: Citation # the full bibliographic info for this source, wrapped in a Citation model


class Claim(BaseModel):
  id: str # e.g., "claim_001" — unique identifier for the claim
  text: str # The prose text of the claim, e.g., "Norway and Russia have a complex geopolitical relationship."
  source_ref: str  # e.g., "[1]" — this should match the Source.ref of the Source that supports this claim, creating a link between the Claim and its Source
  source_id: str  # e.g., "geopolitical/norway_russia" — this links to Source.id

  @field_validator("text")
  @classmethod
  def validate_text(cls, value) -> str:
    """Ensure that the claim text is not empty or just whitespace."""
    if not value.strip():
      raise ValueError("Claim text cannot be empty or whitespace")
    return value



class PIRItem(BaseModel):
  question: str       # the PIR formulated as an intelligence question
  priority: Literal["high", "medium", "low"]
  rationale: str      # why this PIR matters given the context
  source_ids: list[str]  # IDs referencing Source.id entries in the parent PIRResponse


class PIRResponse(BaseModel):
  pir_text: str          # annotated summary paragraph — may contain [N] citation markers
  claims: list[Claim]    # opt-in: only source-backed statements become Claim entries
  sources: list[Source]  # all sources referenced by pir_text claims
  pirs: list[PIRItem]    # the structured PIR questions
  reasoning: str         # transparent explanation of why these PIRs were selected



