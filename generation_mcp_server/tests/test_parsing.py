"""Tests for enrich_pir_response — bridges raw AI output to PIRResponse.

The AI returns sources with id/ref/source_type but no citation metadata.
enrich_pir_response looks up citations from KNOWLEDGE_REGISTRY and attaches them.

Run with: python -m pytest tests/test_parsing.py -v
"""

import json
import pytest

from models import PIRResponse
from resources import enrich_pir_response


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_raw(
    *,
    pir_text="Test assessment",
    claims=None,
    sources=None,
    pirs=None,
    reasoning="Test reasoning",
):
    """Build a minimal raw AI JSON string for testing."""
    return json.dumps({
        "pir_text": pir_text,
        "claims": claims or [],
        "sources": sources or [],
        "pirs": pirs or [{"question": "Q?", "priority": "high", "rationale": "R", "source_ids": []}],
        "reasoning": reasoning,
    })


# ── Group 1: Happy path ───────────────────────────────────────────────────────

def test_enrich_attaches_citation_from_registry():
    raw = _make_raw(
        pir_text="Norway faces elevated risk[1]",
        claims=[{"id": "claim_1", "text": "Norway faces elevated risk", "source_ref": "[1]", "source_id": "geopolitical/norway_russia"}],
        sources=[{"id": "geopolitical/norway_russia", "ref": "[1]", "source_type": "kb"}],
    )
    result = enrich_pir_response(raw)
    assert isinstance(result, PIRResponse)
    assert result.sources[0].citation.author == "Threat Intelligence System"
    assert result.sources[0].citation.title == "Norwegian-Russian Geopolitical Relations"


def test_enrich_preserves_pir_text_and_claims():
    raw = _make_raw(
        pir_text="Norway faces elevated risk[1]",
        claims=[{"id": "claim_1", "text": "Norway faces elevated risk", "source_ref": "[1]", "source_id": "geopolitical/norway_russia"}],
        sources=[{"id": "geopolitical/norway_russia", "ref": "[1]", "source_type": "kb"}],
    )
    result = enrich_pir_response(raw)
    assert "Norway faces elevated risk[1]" in result.pir_text
    assert result.claims[0].source_ref == "[1]"


# ── Group 2: No background knowledge ─────────────────────────────────────────

def test_enrich_accepts_empty_claims_and_sources():
    raw = _make_raw()
    result = enrich_pir_response(raw)
    assert result.claims == []
    assert result.sources == []


# ── Group 3: Unknown source IDs ──────────────────────────────────────────────

def test_enrich_skips_unknown_source_id():
    raw = _make_raw(
        sources=[{"id": "made_up/source", "ref": "[1]", "source_type": "kb"}],
    )
    result = enrich_pir_response(raw)
    assert result.sources == []  # silently dropped


# ── Group 4: Error handling ───────────────────────────────────────────────────

def test_enrich_raises_on_invalid_json():
    with pytest.raises(ValueError, match="invalid"):
        enrich_pir_response("this is not json {{{")


def test_enrich_raises_on_missing_required_fields():
    with pytest.raises(ValueError):
        enrich_pir_response(json.dumps({"claims": [], "sources": [], "pirs": [], "reasoning": "x"}))
        # pir_text is missing


# ── Group 5: Output contract ──────────────────────────────────────────────────

def test_enrich_returns_pir_response_instance():
    raw = _make_raw()
    result = enrich_pir_response(raw)
    assert isinstance(result, PIRResponse)


def test_enrich_result_serialises_to_dict():
    raw = _make_raw()
    result = enrich_pir_response(raw)
    data = result.model_dump()
    assert "pir_text" in data
    assert "claims" in data
    assert "sources" in data
    assert "pirs" in data
    assert "reasoning" in data
