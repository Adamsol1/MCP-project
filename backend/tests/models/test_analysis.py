"""Tests for analysis-phase models."""

import pytest
from pydantic import ValidationError

from src.models.analysis import AnalysisDraft, CouncilNote, ProcessingResult


def _make_processing_payload() -> dict:
    return {
        "findings": [
            {
                "id": "F-001",
                "title": "Credential-access activity",
                "finding": "Repeated authentication attempts targeted privileged accounts.",
                "evidence_summary": "Login failures were followed by successful access.",
                "source": "network_telemetry",
                "confidence": 82,
                "relevant_to": ["PIR-1"],
                "supporting_data": {"attack_ids": ["T1078"]},
                "why_it_matters": "This suggests adversary access development.",
                "uncertainties": ["The compromised account path is unconfirmed."],
            },
            {
                "id": "F-002",
                "title": "Phishing staging",
                "finding": "Lookalike domains appear staged for credential theft.",
                "evidence_summary": "Passive DNS and hosting overlap support staging.",
                "source": "osint",
                "confidence": 76,
                "relevant_to": ["PIR-2"],
                "supporting_data": {"domains": ["example-phish.test"]},
                "why_it_matters": "This supports a parallel intrusion path.",
                "uncertainties": ["Delivery infrastructure remains incomplete."],
            },
        ],
        "gaps": [
            "Attribution remains unresolved.",
            "Victimology requires confirmation.",
        ],
    }


class TestProcessingResult:
    """Test ProcessingResult model."""

    def test_valid_processing_result_payload(self):
        """Session processing result payload should validate successfully."""
        payload = _make_processing_payload()

        result = ProcessingResult.model_validate(payload)

        assert len(result.findings) == 2
        assert len(result.gaps) == 2
        assert result.findings[0].id == "F-001"
        assert result.findings[0].confidence == 82

    def test_invalid_confidence_fails_validation(self):
        """Confidence outside 0-100 should fail validation."""
        payload = _make_processing_payload()
        payload["findings"][0]["confidence"] = 101

        with pytest.raises(ValidationError):
            ProcessingResult.model_validate(payload)

    def test_processing_result_requires_findings_shape(self):
        """Malformed findings should fail validation."""
        payload = _make_processing_payload()
        payload["findings"][1] = {"id": "F-002"}

        with pytest.raises(ValidationError):
            ProcessingResult.model_validate(payload)


class TestAnalysisDraft:
    """Test AnalysisDraft model."""

    def test_valid_analysis_draft_payload(self):
        """AnalysisDraft should validate and serialize correctly."""
        draft = AnalysisDraft(
            summary="Assessment of a coordinated access-development campaign against Nordic telecom infrastructure.",
            key_judgments=[
                "The activity is consistent with targeted credential access and phishing preparation.",
                "Infrastructure overlap suggests a repeatable intrusion playbook rather than isolated noise.",
            ],
            per_perspective_implications={
                "NOR": [
                    "Telecom operators should review privileged access paths tied to resilience functions."
                ],
                "EU": [
                    "Cross-border interconnection dependencies increase the strategic impact of successful access."
                ],
            },
            recommended_actions=[
                "Prioritize credential resets and MFA review for telecom administration accounts.",
                "Expand monitoring for lookalike domains and VPS-hosted login activity.",
            ],
            information_gaps=[
                "Attribution remains unconfirmed.",
                "Direct linkage between phishing infrastructure and account compromise is still missing.",
            ],
        )

        serialized = draft.model_dump()

        assert serialized["summary"].startswith("Assessment of")
        assert len(serialized["key_judgments"]) == 2
        assert serialized["per_perspective_implications"]["NOR"]
        assert len(serialized["recommended_actions"]) == 2


class TestCouncilNote:
    """Test CouncilNote model."""

    def test_valid_council_note_payload(self):
        """CouncilNote should validate a stable council response payload."""
        note = CouncilNote(
            status="complete",
            question="Assess whether the phishing staging indicates deliberate access development.",
            participants=["US Strategic Analyst", "Neutral Evidence Analyst"],
            rounds_completed=2,
            summary="The council assessed the activity as coordinated access development against telecom operations.",
            key_agreements=[
                "The findings support a targeted access-development pattern.",
                "Attribution remains too weak for actor-specific conclusions.",
            ],
            key_disagreements=[
                "Participants diverged on whether disruption preparation is likely."
            ],
            final_recommendation="Prioritize validation of affected accounts and correlate infrastructure overlap before escalating attribution claims.",
            full_debate=[
                {
                    "round": 1,
                    "participant": "US Strategic Analyst",
                    "response": "The credential and phishing pattern is consistent with deliberate access preparation.",
                    "timestamp": "2026-03-20T10:00:00Z",
                }
            ],
            transcript_path="backend/data/outputs/council_transcripts/demo.md",
        )

        assert note.rounds_completed == 2
        assert note.participants[0] == "US Strategic Analyst"
        assert note.full_debate[0].participant == "US Strategic Analyst"

    def test_council_note_serialization(self):
        """CouncilNote should serialize with stable frontend-facing fields."""
        note = CouncilNote(
            status="complete",
            question="Assess the selected findings.",
            participants=["US Strategic Analyst", "Neutral Evidence Analyst"],
            rounds_completed=2,
            summary="Consensus summary.",
            key_agreements=["Agreement A"],
            key_disagreements=["Disagreement A"],
            final_recommendation="Recommendation A",
            full_debate=[
                {
                    "round": 1,
                    "participant": "Neutral Evidence Analyst",
                    "response": "Evidence is sufficient for a cautious assessment.",
                    "timestamp": "2026-03-20T10:05:00Z",
                }
            ],
            transcript_path=None,
        )

        serialized = note.model_dump()

        assert set(serialized) == {
            "status",
            "question",
            "participants",
            "rounds_completed",
            "summary",
            "key_agreements",
            "key_disagreements",
            "final_recommendation",
            "full_debate",
            "transcript_path",
        }
        assert serialized["full_debate"][0]["participant"] == "Neutral Evidence Analyst"
