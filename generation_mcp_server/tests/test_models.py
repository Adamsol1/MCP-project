"""Tests for Pydantic response models.

Written first — implementation in src/models.py comes after.
Run with: python -m pytest tests/test_models.py -v
"""

import pytest
from pydantic import ValidationError

from src.models import Citation, Claim, PIRItem, PIRResponse, Source


# ── Group 1: Citation ────────────────────────────────────────────────────────
# The innermost leaf model. No dependencies on other models.
# Maps directly to APA7th fields: author, year, title, publisher.


def test_citation_accepts_valid_fields():
    citation = Citation(
        author="Threat Intelligence System",
        year="2025",
        title="Norwegian-Russian Geopolitical Relations",
        publisher="Internal Knowledge Bank",
    )
    assert citation.author == "Threat Intelligence System"
    assert citation.year == "2025"
    assert citation.title == "Norwegian-Russian Geopolitical Relations"
    assert citation.publisher == "Internal Knowledge Bank"


def test_citation_rejects_missing_required_field():
    with pytest.raises(ValidationError):
        Citation(author="System", year="2025", title="Title")
        # publisher is missing — all four fields are required


def test_citation_rejects_non_string_year():
    with pytest.raises(ValidationError):
        Citation(
            author="Threat Intelligence System",
            year=2025,  # int, not str — strict mode should reject this
            title="Norwegian-Russian Geopolitical Relations",
            publisher="Internal Knowledge Bank",
        )


# ── Group 2: Source ──────────────────────────────────────────────────────────
# Wraps a Citation and adds identity fields.
# source_type drives the UI badge: [KB], [DOC], [SRC].
# It is a Literal — only three valid values.


def test_source_accepts_valid_kb_type():
    citation = Citation(
        author="Threat Intelligence System",
        year="2025",
        title="Norwegian-Russian Geopolitical Relations",
        publisher="Internal Knowledge Bank",
    )
    source = Source(
        id="geopolitical/norway_russia",
        ref="[1]",
        source_type="kb",
        citation=citation,
    )
    assert source.id == "geopolitical/norway_russia"
    assert source.ref == "[1]"
    assert source.source_type == "kb"
    assert source.citation.title == "Norwegian-Russian Geopolitical Relations"


def test_source_rejects_invalid_source_type():
    with pytest.raises(ValidationError):
        Source(
            id="geopolitical/norway_russia",
            ref="[1]",
            source_type="knowledge_bank",  # not in Literal["kb", "doc", "data"]
            citation=Citation(author="S", year="2025", title="T", publisher="P"),
        )


@pytest.mark.parametrize("source_type", ["kb", "doc", "data"])
def test_source_accepts_all_three_valid_types(source_type):
    source = Source(
        id="test_source",
        ref="[1]",
        source_type=source_type,
        citation=Citation(author="S", year="2025", title="T", publisher="P"),
    )
    assert source.source_type == source_type


# ── Group 3: Claim ───────────────────────────────────────────────────────────
# Bridges prose text to a citation.
# source_ref is the display marker ("[1]").
# source_id is the registry lookup key ("geopolitical/norway_russia").
# Both are required — they serve different purposes.


def test_claim_accepts_valid_fields():
    claim = Claim(
        id="claim_1",
        text="Norway's energy infrastructure faces elevated risk from Arctic tensions",
        source_ref="[1]",
        source_id="geopolitical/norway_russia",
    )
    assert claim.id == "claim_1"
    assert claim.source_ref == "[1]"
    assert claim.source_id == "geopolitical/norway_russia"


def test_claim_rejects_empty_text():
    with pytest.raises(ValidationError):
        Claim(
            id="claim_1",
            text="",  # empty string means the parser found no claim — reject it
            source_ref="[1]",
            source_id="geopolitical/norway_russia",
        )


# ── Group 4: PIRResponse ─────────────────────────────────────────────────────
# The top-level model returned by the server.
# Composes everything above. This is what the frontend receives.
#
# Claims are OPT-IN, not required for every sentence.
# pir_text may contain sentences with no [N] marker — those render as plain prose.
# Only verifiable, source-backed statements become Claim entries.
# This preserves analytic nuance while keeping citations honest.


def test_pir_response_accepts_valid_structure():
    citation = Citation(
        author="Threat Intelligence System",
        year="2025",
        title="Norwegian-Russian Geopolitical Relations",
        publisher="Internal Knowledge Bank",
    )
    source = Source(
        id="geopolitical/norway_russia",
        ref="[1]",
        source_type="kb",
        citation=citation,
    )
    claim = Claim(
        id="claim_1",
        text="Norway's energy infrastructure faces elevated risk from Arctic tensions",
        source_ref="[1]",
        source_id="geopolitical/norway_russia",
    )
    pir = PIRItem(
        question="What is the current threat level to Norwegian energy infrastructure?",
        priority="high",
        rationale="Energy infrastructure is a primary target given Arctic tensions.",
        source_ids=["geopolitical/norway_russia"],
    )
    response = PIRResponse(
        pir_text="Norway's energy infrastructure faces elevated risk[1]",
        claims=[claim],
        sources=[source],
        pirs=[pir],
        reasoning="Selected due to known Russian targeting of energy infrastructure.",
    )

    assert response.pir_text.startswith("Norway")
    assert len(response.claims) == 1
    assert len(response.sources) == 1
    assert len(response.pirs) == 1
    # The claim's source_id must match the source's id — referential integrity
    assert response.claims[0].source_id == response.sources[0].id


def test_pir_response_accepts_empty_citation_lists():
    # claims and sources can be empty when no background knowledge is available
    pir = PIRItem(
        question="What is the threat level to Norwegian infrastructure?",
        priority="high",
        rationale="General assessment.",
        source_ids=[],
    )
    response = PIRResponse(
        pir_text="General threat assessment with no specific sources",
        claims=[],
        sources=[],
        pirs=[pir],
        reasoning="Generated without background knowledge.",
    )
    assert response.claims == []
    assert response.sources == []


def test_pir_response_serialises_to_dict():
    pir = PIRItem(
        question="Test PIR question?",
        priority="medium",
        rationale="Test rationale.",
        source_ids=[],
    )
    response = PIRResponse(
        pir_text="Test PIR text",
        claims=[],
        sources=[],
        pirs=[pir],
        reasoning="Test reasoning.",
    )
    data = response.model_dump()  # Pydantic v2 — NOT .dict()
    assert "pir_text" in data
    assert "claims" in data
    assert "sources" in data
    assert "pirs" in data
    assert "reasoning" in data
    assert isinstance(data["claims"], list)
    assert isinstance(data["sources"], list)
    assert isinstance(data["pirs"], list)


def test_pir_response_rejects_missing_pir_text():
    with pytest.raises(ValidationError):
        PIRResponse(claims=[], sources=[], pirs=[], reasoning="test")
        # pir_text is the primary content field — it cannot be absent


def test_pir_response_allows_unclaimed_sentences():
    # Option C: not every sentence in pir_text needs a [N] marker.
    # Here the pir_text has two sentences; only one maps to a claim.
    # The second sentence is analytic prose with no source — valid.
    citation = Citation(
        author="Threat Intelligence System",
        year="2025",
        title="Norwegian-Russian Geopolitical Relations",
        publisher="Internal Knowledge Bank",
    )
    source = Source(
        id="geopolitical/norway_russia",
        ref="[1]",
        source_type="kb",
        citation=citation,
    )
    claim = Claim(
        id="claim_1",
        text="Norway's energy infrastructure faces elevated risk",
        source_ref="[1]",
        source_id="geopolitical/norway_russia",
    )
    pir = PIRItem(
        question="What is the current threat to Norwegian energy infrastructure?",
        priority="high",
        rationale="Energy sector is vulnerable.",
        source_ids=["geopolitical/norway_russia"],
    )
    response = PIRResponse(
        pir_text=(
            "Norway's energy infrastructure faces elevated risk[1]. "
            "This warrants continuous monitoring."  # no marker — analytic prose
        ),
        claims=[claim],   # only one claim despite two sentences
        sources=[source],
        pirs=[pir],
        reasoning="Priority given to energy infrastructure based on known threat patterns.",
    )
    assert len(response.claims) == 1
    assert len(response.sources) == 1
    assert "[1]" not in response.claims[0].text  # the marker lives in pir_text, not claim text
