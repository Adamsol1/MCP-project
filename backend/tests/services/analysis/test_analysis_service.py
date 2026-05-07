import json
import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

from src.models.analysis import AnalysisDraft, FindingModel, ProcessingResult
from src.models.confidence import PerspectiveAssertion
from src.services.analysis.analysis_service import AnalysisService


def _make_finding(id="f1", title="Finding 1", confidence=70, source="open_source"):
    return FindingModel(
        id=id,
        title=title,
        finding="Test finding statement",
        evidence_summary="Test evidence summary",
        why_it_matters="It matters for security",
        confidence=confidence,
        source=source,
        supporting_data={},
    )


def _make_processing_result(findings=None, gaps=None):
    return ProcessingResult(
        findings=findings if findings is not None else [_make_finding()],
        gaps=gaps if gaps is not None else ["Attribution unresolved"],
    )


def _make_draft(title="Title", summary="Summary", perspectives=None):
    return AnalysisDraft(
        title=title,
        summary=summary,
        key_judgments=["Key judgment 1"],
        per_perspective_implications=perspectives or {
            "us": [PerspectiveAssertion(assertion="US assertion", supporting_finding_ids=[])]
        },
        recommended_actions=["Recommended action"],
        information_gaps=[],
    )


class TestNormalizePerspectives:
    def setup_method(self):
        self.service = AnalysisService(mcp_client=MagicMock())

    def test_returns_all_defaults_when_none_given(self):
        # arrange — no selected perspectives

        # act
        result = self.service._normalize_perspectives(None)

        # assert
        assert len(result) > 0
        assert "us" in result
        assert "norway" in result

    def test_returns_all_defaults_when_empty_list_given(self):
        # arrange
        selected = []

        # act
        result = self.service._normalize_perspectives(selected)

        # assert
        assert len(result) > 0

    def test_keeps_only_valid_perspectives(self):
        # arrange
        selected = ["us", "norway"]

        # act
        result = self.service._normalize_perspectives(selected)

        # assert
        assert result == ["us", "norway"]

    def test_filters_out_invalid_perspective_names(self):
        # arrange
        selected = ["us", "invalid_country", "norway"]

        # act
        result = self.service._normalize_perspectives(selected)

        # assert
        assert "us" in result
        assert "norway" in result
        assert "invalid_country" not in result

    def test_returns_defaults_when_all_values_are_invalid(self):
        # arrange
        selected = ["invalid1", "invalid2"]

        # act
        result = self.service._normalize_perspectives(selected)

        # assert
        assert len(result) > 0


class TestBuildFallbackDraft:
    def setup_method(self):
        self.service = AnalysisService(mcp_client=MagicMock())

    def test_returns_analysis_draft_with_findings(self):
        # arrange
        processing_result = _make_processing_result(findings=[_make_finding()])

        # act
        draft = self.service._build_fallback_draft(processing_result, ["us", "norway"])

        # assert
        assert isinstance(draft, AnalysisDraft)
        assert len(draft.key_judgments) > 0

    def test_includes_only_selected_perspectives(self):
        # arrange
        processing_result = _make_processing_result()

        # act
        draft = self.service._build_fallback_draft(processing_result, ["us"])

        # assert
        assert "us" in draft.per_perspective_implications
        assert "norway" not in draft.per_perspective_implications

    def test_handles_no_findings_gracefully(self):
        # arrange
        processing_result = _make_processing_result(findings=[], gaps=["Big gap"])

        # act
        draft = self.service._build_fallback_draft(processing_result, ["neutral"])

        # assert
        assert "No validated findings" in draft.key_judgments[0]

    def test_builds_norwegian_draft_when_language_is_no(self):
        # arrange
        processing_result = _make_processing_result()

        # act
        draft = self.service._build_fallback_draft(processing_result, ["norway"], language="no")

        # assert
        assert isinstance(draft, AnalysisDraft)
        assert draft.summary is not None

    def test_summary_references_finding_count(self):
        # arrange
        findings = [_make_finding("f1"), _make_finding("f2")]
        processing_result = _make_processing_result(findings=findings)

        # act
        draft = self.service._build_fallback_draft(processing_result, ["neutral"])

        # assert
        assert "2" in draft.summary


class TestMergeWithFallback:
    def setup_method(self):
        self.service = AnalysisService(mcp_client=MagicMock())

    def test_uses_llm_title(self):
        # arrange
        llm = _make_draft(title="LLM Title", summary="LLM summary")
        fallback = _make_draft(title="Fallback Title", summary="Fallback summary")

        # act
        result = self.service._merge_with_fallback(llm, fallback)

        # assert
        assert result.title == "LLM Title"

    def test_falls_back_to_fallback_summary_when_llm_is_empty(self):
        # arrange
        llm = _make_draft(summary="")
        fallback = _make_draft(summary="Fallback summary")

        # act
        result = self.service._merge_with_fallback(llm, fallback)

        # assert
        assert result.summary == "Fallback summary"

    def test_uses_fallback_implications_when_llm_has_empty_list(self):
        # arrange
        llm = _make_draft(perspectives={"us": []})
        fallback = _make_draft(perspectives={
            "us": [PerspectiveAssertion(assertion="Fallback assertion", supporting_finding_ids=[])]
        })

        # act
        result = self.service._merge_with_fallback(llm, fallback)

        # assert
        assert len(result.per_perspective_implications["us"]) == 1
        assert result.per_perspective_implications["us"][0].assertion == "Fallback assertion"

    def test_includes_fallback_only_perspectives_not_in_llm(self):
        # arrange
        llm = _make_draft(perspectives={"us": []})
        fallback = _make_draft(perspectives={
            "us": [],
            "norway": [PerspectiveAssertion(assertion="Norway assertion", supporting_finding_ids=[])],
        })

        # act
        result = self.service._merge_with_fallback(llm, fallback)

        # assert
        assert "norway" in result.per_perspective_implications


class TestGenerateDraft:
    @pytest.mark.asyncio
    async def test_merges_selected_perspective_outputs_and_filters_finding_ids(self):
        # arrange
        mock_client = MagicMock()

        @asynccontextmanager
        async def mock_connect():
            yield mock_client

        mock_client.connect = mock_connect
        mock_client.read_resource = AsyncMock(side_effect=lambda uri: f"persona:{uri}")
        mock_client.get_prompt = AsyncMock(return_value="analysis task prompt")

        us_payload = {
            "title": "Telecom access campaign",
            "summary": "Credential access suggests deliberate telecom targeting.",
            "key_judgments": ["Privileged access is the main risk."],
            "per_perspective_implications": {
                "us": [
                    {
                        "assertion": "US operators should harden identity paths.",
                        "supporting_finding_ids": ["f1", "not-a-real-finding"],
                    }
                ]
            },
            "recommended_actions": ["Review privileged access."],
            "information_gaps": ["Should be replaced by fallback gaps."],
        }
        norway_payload = {
            **us_payload,
            "per_perspective_implications": {
                "norway": [
                    {
                        "assertion": "Norwegian telecom operators should prioritize NOC access review.",
                        "supporting_finding_ids": ["f1"],
                    }
                ]
            },
        }

        with pytest.MonkeyPatch().context():
            from unittest.mock import patch

            with patch("src.services.analysis.analysis_service.GeminiAgent") as MockAgent:
                first_agent = MagicMock()
                first_agent.run = AsyncMock(return_value=json.dumps(us_payload))
                second_agent = MagicMock()
                second_agent.run = AsyncMock(return_value=json.dumps(norway_payload))
                MockAgent.side_effect = [first_agent, second_agent]

                service = AnalysisService(
                    mcp_client=mock_client,
                    perspective_docs={"us": "US reference doctrine"},
                )

                # act
                draft, enriched = await service.generate_draft(
                    _make_processing_result(),
                    selected_perspectives=["us", "norway"],
                    pir="How is telecom access being developed?",
                )

        # assert
        assert draft.title == "Telecom access campaign"
        assert set(draft.per_perspective_implications) == {"us", "norway"}
        assert draft.per_perspective_implications["us"][0].supporting_finding_ids == [
            "f1"
        ]
        assert draft.per_perspective_implications["us"][0].confidence is not None
        assert enriched.findings[0].computed_confidence is not None
        assert "US reference doctrine" in first_agent.run.await_args.kwargs["system_prompt"]
        assert (
            "US reference doctrine"
            not in second_agent.run.await_args.kwargs["system_prompt"]
        )

    @pytest.mark.asyncio
    async def test_returns_fallback_draft_when_mcp_connection_fails(self):
        # arrange
        mock_client = MagicMock()

        @asynccontextmanager
        async def failing_connect():
            raise Exception("MCP server unavailable")
            yield

        mock_client.connect = failing_connect
        service = AnalysisService(mcp_client=mock_client)

        # act
        draft, enriched = await service.generate_draft(
            _make_processing_result(),
            selected_perspectives=["us"],
        )

        # assert
        assert isinstance(draft, AnalysisDraft)
        assert "us" in draft.per_perspective_implications

    @pytest.mark.asyncio
    async def test_returns_fallback_draft_when_no_agent_produces_output(self):
        # arrange
        mock_client = MagicMock()

        @asynccontextmanager
        async def mock_connect():
            yield mock_client

        mock_client.connect = mock_connect
        mock_client.read_resource = AsyncMock(return_value="persona text")
        mock_client.get_prompt = AsyncMock(return_value="task prompt")

        with pytest.MonkeyPatch().context() as mp:
            from unittest.mock import patch
            with patch("src.services.analysis.analysis_service.GeminiAgent") as MockAgent:
                mock_agent = MagicMock()
                mock_agent.run = AsyncMock(return_value="not json at all")
                MockAgent.return_value = mock_agent

                service = AnalysisService(mcp_client=mock_client)

                # act
                draft, enriched = await service.generate_draft(
                    _make_processing_result(),
                    selected_perspectives=["us"],
                )

        # assert
        assert isinstance(draft, AnalysisDraft)
