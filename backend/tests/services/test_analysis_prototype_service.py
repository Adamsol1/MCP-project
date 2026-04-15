"""Tests for the analysis prototype service."""

import json

import pytest

from src.models.analysis import AnalysisDraft, ProcessingResult
from src.models.confidence import AssertionConfidence, PerspectiveAssertion
from src.services import processing_prototype_service as processing_service_module
from src.services.analysis_prototype_service import AnalysisPrototypeService
from src.services.processing_prototype_service import ProcessingPrototypeService

VALID_PROCESSING_PAYLOAD = {
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
        }
    ],
    "gaps": ["Attribution remains unresolved."],
}


def _write_processed_json(tmp_path, session_id: str) -> None:
    session_dir = tmp_path / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "processed.json").write_text(
        json.dumps({"attempts": [json.dumps(VALID_PROCESSING_PAYLOAD)]}),
        encoding="utf-8",
    )


class _FakeLLMService:
    """Fake LLM service that returns PerspectiveAssertion-shaped implications."""

    async def generate_json(self, prompt: str) -> dict:
        assert "Processed findings" in prompt
        assert "supporting_finding_ids" in prompt  # new prompt shape
        return {
            "summary": "LLM-generated assessment of the processed findings.",
            "key_judgments": [
                "Credential-access activity and phishing staging reinforce a coordinated access-development assessment."
            ],
            "per_perspective_implications": {
                "us": [
                    {"assertion": "US implication A", "supporting_finding_ids": ["F-001"]},
                    {"assertion": "US implication B", "supporting_finding_ids": []},
                ],
                "norway": [
                    {"assertion": "Norway implication A", "supporting_finding_ids": ["F-001"]},
                    {"assertion": "Norway implication B", "supporting_finding_ids": []},
                ],
                "china": [
                    {"assertion": "China implication A", "supporting_finding_ids": []},
                    {"assertion": "China implication B", "supporting_finding_ids": []},
                ],
                "eu": [
                    {"assertion": "EU implication A", "supporting_finding_ids": []},
                    {"assertion": "EU implication B", "supporting_finding_ids": []},
                ],
                "russia": [
                    {"assertion": "Russia implication A", "supporting_finding_ids": []},
                    {"assertion": "Russia implication B", "supporting_finding_ids": []},
                ],
                "neutral": [
                    {"assertion": "Neutral implication A", "supporting_finding_ids": ["F-001"]},
                    {"assertion": "Neutral implication B", "supporting_finding_ids": []},
                ],
            },
            "recommended_actions": [
                "Review telecom administrator exposure and related phishing infrastructure."
            ],
            "information_gaps": [
                "Attribution remains unresolved.",
                "Victimology requires confirmation.",
            ],
        }


class _FakeLLMServiceWithHallucinatedIds:
    """Returns implications with hallucinated finding IDs that should be stripped."""

    async def generate_json(self, prompt: str) -> dict:
        del prompt
        return {
            "summary": "Summary.",
            "key_judgments": ["Judgment."],
            "per_perspective_implications": {
                "us": [
                    {
                        "assertion": "US claim with bad ID",
                        "supporting_finding_ids": ["F-001", "HALLUCINATED-99"],
                    }
                ],
                "norway": [],
                "china": [],
                "eu": [],
                "russia": [],
                "neutral": [],
            },
            "recommended_actions": [],
            "information_gaps": [],
        }


class _FakeLLMServiceOldStringFormat:
    """Simulates an LLM that returns old string-list format (should fall back gracefully)."""

    async def generate_json(self, prompt: str) -> dict:
        del prompt
        return {
            "summary": "Summary.",
            "key_judgments": [],
            "per_perspective_implications": {
                "us": ["This is a plain string, not a dict"],
            },
            "recommended_actions": [],
            "information_gaps": [],
        }


class TestAnalysisPrototypeService:
    """Test AnalysisPrototypeService."""

    @pytest.mark.asyncio
    async def test_generates_draft_from_valid_processing_result(
        self, monkeypatch, tmp_path
    ):
        """Service should generate a grounded draft from a valid ProcessingResult."""
        monkeypatch.setattr(processing_service_module, "_SESSIONS_DATA_DIR", tmp_path)
        _write_processed_json(tmp_path, "session-123")
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-123"
        )

        draft, _ = await AnalysisPrototypeService(
            llm_service=_FakeLLMService()
        ).generate_draft(processing_result)

        joined_judgments = " ".join(draft.key_judgments).lower()

        assert isinstance(draft, AnalysisDraft)
        assert draft.key_judgments
        assert "credential-access" in joined_judgments

    @pytest.mark.asyncio
    async def test_summary_is_non_empty(self, monkeypatch, tmp_path):
        """Generated summary should not be empty."""
        monkeypatch.setattr(processing_service_module, "_SESSIONS_DATA_DIR", tmp_path)
        _write_processed_json(tmp_path, "session-456")
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-456"
        )

        draft, _ = await AnalysisPrototypeService(
            llm_service=_FakeLLMService()
        ).generate_draft(processing_result)

        assert draft.summary.strip() != ""

    @pytest.mark.asyncio
    async def test_gaps_propagated_into_information_gaps(self, monkeypatch, tmp_path):
        """Processing gaps should be propagated into the draft."""
        monkeypatch.setattr(processing_service_module, "_SESSIONS_DATA_DIR", tmp_path)
        _write_processed_json(tmp_path, "session-789")
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-789"
        )

        draft, _ = await AnalysisPrototypeService(
            llm_service=_FakeLLMService()
        ).generate_draft(processing_result)

        assert draft.information_gaps == processing_result.gaps

    @pytest.mark.asyncio
    async def test_per_perspective_implications_contains_expected_keys(
        self, monkeypatch, tmp_path
    ):
        """Draft should include the canonical perspective keys."""
        monkeypatch.setattr(processing_service_module, "_SESSIONS_DATA_DIR", tmp_path)
        _write_processed_json(tmp_path, "session-999")
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-999"
        )

        draft, _ = await AnalysisPrototypeService(
            llm_service=_FakeLLMService()
        ).generate_draft(processing_result)

        assert set(draft.per_perspective_implications) >= {
            "us",
            "norway",
            "china",
            "eu",
            "russia",
            "neutral",
        }

    @pytest.mark.asyncio
    async def test_per_perspective_implications_are_perspective_assertion_objects(
        self, monkeypatch, tmp_path
    ):
        """Each implication must be a PerspectiveAssertion with a confidence."""
        monkeypatch.setattr(processing_service_module, "_SESSIONS_DATA_DIR", tmp_path)
        _write_processed_json(tmp_path, "session-asserts")
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-asserts"
        )

        draft, _ = await AnalysisPrototypeService(
            llm_service=_FakeLLMService()
        ).generate_draft(processing_result)

        for perspective, assertions in draft.per_perspective_implications.items():
            for assertion in assertions:
                assert isinstance(assertion, PerspectiveAssertion), (
                    f"{perspective}: expected PerspectiveAssertion, got {type(assertion)}"
                )
                assert assertion.confidence is not None, (
                    f"{perspective}: confidence should be set after enrichment"
                )
                assert isinstance(assertion.confidence, AssertionConfidence)

    @pytest.mark.asyncio
    async def test_hallucinated_finding_ids_stripped(self, monkeypatch, tmp_path):
        """Finding IDs not in ProcessingResult must be stripped without crash."""
        monkeypatch.setattr(processing_service_module, "_SESSIONS_DATA_DIR", tmp_path)
        _write_processed_json(tmp_path, "session-hallucinated")
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-hallucinated"
        )

        draft, _ = await AnalysisPrototypeService(
            llm_service=_FakeLLMServiceWithHallucinatedIds()
        ).generate_draft(processing_result)

        us_assertions = draft.per_perspective_implications.get("us", [])
        if us_assertions:
            fids = us_assertions[0].supporting_finding_ids
            assert "HALLUCINATED-99" not in fids

    @pytest.mark.asyncio
    async def test_enriched_processing_result_has_computed_confidence(
        self, monkeypatch, tmp_path
    ):
        """generate_draft should return an enriched ProcessingResult with computed_confidence set."""
        monkeypatch.setattr(processing_service_module, "_SESSIONS_DATA_DIR", tmp_path)
        _write_processed_json(tmp_path, "session-enriched")
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-enriched"
        )

        _, enriched = await AnalysisPrototypeService(
            llm_service=_FakeLLMService()
        ).generate_draft(processing_result)

        assert isinstance(enriched, ProcessingResult)
        for finding in enriched.findings:
            assert finding.computed_confidence is not None, (
                f"Finding {finding.id} should have computed_confidence set"
            )

    @pytest.mark.asyncio
    async def test_fallback_used_when_llm_returns_old_string_format(
        self, monkeypatch, tmp_path
    ):
        """Old string-format implications should trigger fallback, not a crash."""
        monkeypatch.setattr(processing_service_module, "_SESSIONS_DATA_DIR", tmp_path)
        _write_processed_json(tmp_path, "session-old-format")
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-old-format"
        )

        draft, _ = await AnalysisPrototypeService(
            llm_service=_FakeLLMServiceOldStringFormat()
        ).generate_draft(processing_result)

        # Should fall back to fallback_draft — summary must still be non-empty
        assert isinstance(draft, AnalysisDraft)
        assert draft.summary.strip() != ""
