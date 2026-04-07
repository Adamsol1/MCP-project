"""Analysis-stage council wrapper using app runtime defaults."""

import sys
from pathlib import Path
from types import SimpleNamespace

from src.models.analysis import (
    AnalysisDraft,
    CouncilNote,
    CouncilRunSettings,
    CouncilRuntimeProfile,
    CouncilTranscriptEntry,
    ProcessingResult,
)
from src.models.dialogue import Perspective
from src.services.council_personas import get_council_persona
from src.services.gemini_deliberation_adapter import GeminiDeliberationAdapter

COUNCIL_MCP_DIR = Path(__file__).resolve().parents[3] / "council_mcp"
if str(COUNCIL_MCP_DIR) not in sys.path:
    sys.path.insert(0, str(COUNCIL_MCP_DIR))

from deliberation.engine import DeliberationEngine  # type: ignore  # noqa: E402
from deliberation.transcript import TranscriptManager  # type: ignore  # noqa: E402
from models.schema import DeliberateRequest, Participant  # type: ignore  # noqa: E402


class CouncilService:
    """Run a council deliberation with fixed app defaults."""

    DEFAULT_ADAPTER = "gemini"
    DEFAULT_MODEL = "gemini-2.5-flash"
    DEFAULT_MODE = "conference"
    DEFAULT_ROUNDS = 2
    DEFAULT_TIMEOUT_PER_ROUND = 180
    DEFAULT_VOTE_RETRY_ENABLED = True
    DEFAULT_VOTE_RETRY_ATTEMPTS = 1
    FILE_TREE_INJECTION_ENABLED = False
    DECISION_GRAPH_ENABLED = False

    def __init__(self, working_directory: str | Path | None = None):
        if working_directory is None:
            working_directory = (
                Path(__file__).resolve().parents[2] / "data" / "outputs"
            )
        self.working_directory = Path(working_directory)
        self.working_directory.mkdir(parents=True, exist_ok=True)
        self.transcript_dir = self.working_directory / "council_transcripts"
        self.transcript_dir.mkdir(parents=True, exist_ok=True)

    def resolve_runtime_profile(
        self, council_settings: CouncilRunSettings | None = None
    ) -> CouncilRuntimeProfile:
        settings = council_settings or CouncilRunSettings()
        return CouncilRuntimeProfile(
            adapter=self.DEFAULT_ADAPTER,
            model=self.DEFAULT_MODEL,
            mode=settings.mode,
            rounds=settings.rounds,
            timeout_per_round_seconds=settings.timeout_seconds,
            vote_retry_enabled=settings.vote_retry_enabled,
            vote_retry_attempts=settings.vote_retry_attempts,
            working_directory=str(self.working_directory),
            file_tree_injection_enabled=self.FILE_TREE_INJECTION_ENABLED,
            decision_graph_enabled=self.DECISION_GRAPH_ENABLED,
        )

    @property
    def runtime_profile(self) -> CouncilRuntimeProfile:
        return self.resolve_runtime_profile()

    def _normalize_perspectives(
        self, selected_perspectives: list[str]
    ) -> list[Perspective]:
        normalized: list[Perspective] = []
        seen: set[Perspective] = set()
        for perspective_name in selected_perspectives:
            perspective = Perspective(perspective_name.lower())
            if perspective in seen:
                continue
            seen.add(perspective)
            normalized.append(perspective)
        return normalized

    def build_participants(self, selected_perspectives: list[str]) -> list[Participant]:
        normalized = self._normalize_perspectives(selected_perspectives)
        if len(normalized) < 2:
            raise ValueError("At least 2 perspectives are required for council deliberation")

        participants = []
        for perspective in normalized:
            persona = get_council_persona(perspective)
            participants.append(
                Participant(
                    cli=self.DEFAULT_ADAPTER,
                    model=self.DEFAULT_MODEL,
                    display_name=persona.display_name,
                    persona_prompt=persona.persona_prompt,
                )
            )
        return participants

    def build_question(
        self,
        debate_point: str,
        selected_findings,
    ) -> str:
        cleaned_point = debate_point.strip()
        if cleaned_point:
            return cleaned_point
        finding_labels = ", ".join(f"{finding.id}: {finding.title}" for finding in selected_findings)
        return f"Assess the strongest interpretation and strategic implications of findings {finding_labels}."

    def build_context(
        self,
        processing_result: ProcessingResult,
        analysis_draft: AnalysisDraft,
        debate_point: str,
        selected_findings=None,
    ) -> str:
        findings = list(selected_findings) if selected_findings is not None else processing_result.findings

        finding_blocks = []
        for finding in findings:
            finding_blocks.append(
                "\n".join(
                    [
                        f"- {finding.id} | {finding.title}",
                        f"  Finding: {finding.finding}",
                        f"  Evidence: {finding.evidence_summary}",
                        f"  Why it matters: {finding.why_it_matters}",
                        f"  Confidence: {finding.confidence}/100",
                        f"  Relevant PIRs: {', '.join(finding.relevant_to) if finding.relevant_to else 'None'}",
                        f"  Uncertainties: {'; '.join(finding.uncertainties)}",
                    ]
                )
            )

        context_sections = [
            "## Analysis Draft Summary",
            analysis_draft.summary,
            "",
            "## Key Judgments",
            *[f"- {judgment}" for judgment in analysis_draft.key_judgments],
            "",
            "## Recommended Actions",
            *[f"- {action}" for action in analysis_draft.recommended_actions],
            "",
            "## Information Gaps",
            *[f"- {gap}" for gap in analysis_draft.information_gaps],
            "",
            "## Findings In Scope",
            *finding_blocks,
        ]

        if debate_point.strip():
            context_sections.extend(["", "## Debate Focus", debate_point.strip()])

        return "\n".join(context_sections)

    def build_request(
        self,
        debate_point: str,
        selected_perspectives: list[str],
        processing_result: ProcessingResult,
        analysis_draft: AnalysisDraft,
        council_settings: CouncilRunSettings | None = None,
        selected_findings=None,
    ) -> DeliberateRequest:
        runtime_profile = self.resolve_runtime_profile(council_settings)
        participants = self.build_participants(selected_perspectives)
        question = self.build_question(debate_point, selected_findings or [])
        context = self.build_context(
            processing_result=processing_result,
            analysis_draft=analysis_draft,
            debate_point=debate_point,
            selected_findings=selected_findings,
        )

        return DeliberateRequest(
            question=question,
            participants=participants,
            rounds=runtime_profile.rounds,
            mode=runtime_profile.mode,
            context=context,
            working_directory=runtime_profile.working_directory,
        )

    def _build_engine(self, runtime_profile: CouncilRuntimeProfile):
        adapter = GeminiDeliberationAdapter(timeout=180)
        adapters = {self.DEFAULT_ADAPTER: adapter}
        config = SimpleNamespace(
            defaults=SimpleNamespace(
                timeout_per_round=runtime_profile.timeout_per_round_seconds,
                rounds=runtime_profile.rounds,
            ),
            deliberation=SimpleNamespace(
                convergence_detection=SimpleNamespace(enabled=False),
                file_tree=SimpleNamespace(
                    enabled=runtime_profile.file_tree_injection_enabled,
                    max_depth=0,
                    max_files=0,
                ),
                tool_security=SimpleNamespace(
                    exclude_patterns=[],
                    max_file_size_bytes=1_048_576,
                ),
                vote_retry=SimpleNamespace(
                    enabled=runtime_profile.vote_retry_enabled,
                    max_retries=runtime_profile.vote_retry_attempts,
                    min_response_length=100,
                ),
            ),
            decision_graph=SimpleNamespace(
                enabled=runtime_profile.decision_graph_enabled
            ),
        )
        transcript_manager = TranscriptManager(output_dir=str(self.transcript_dir))
        engine = DeliberationEngine(
            adapters=adapters,
            transcript_manager=transcript_manager,
            config=config,
        )
        # App analysis-stage councils should debate from the prepared dossier only.
        # Disabling tool access avoids prompt contamination from transcript/output files.
        engine.tool_executor = None
        engine.tool_execution_history = []
        return engine

    def _raise_if_runtime_failed(self, result) -> None:
        responses = list(result.full_debate)
        if not responses:
            raise RuntimeError("Council runtime failed: no participant responses were produced")

        if any(not entry.response.startswith("[ERROR:") for entry in responses):
            return

        first_error = responses[0].response.strip("[]")
        if "API key" in first_error or "api key" in first_error:
            raise RuntimeError(
                "Council runtime failed: Gemini API access is not configured correctly for the backend process."
            )
        raise RuntimeError(f"Council runtime failed: {first_error}")

    async def run_council(
        self,
        session_id: str,
        debate_point: str,
        selected_perspectives: list[str],
        processing_result: ProcessingResult,
        analysis_draft: AnalysisDraft,
        finding_ids: list[str] | None = None,
        council_settings: CouncilRunSettings | None = None,
    ) -> CouncilNote:
        del session_id
        runtime_profile = self.resolve_runtime_profile(council_settings)
        selected_findings = (
            [finding for finding in processing_result.findings if finding.id in finding_ids]
            if finding_ids
            else processing_result.findings
        )
        request = self.build_request(
            debate_point=debate_point,
            selected_perspectives=selected_perspectives,
            processing_result=processing_result,
            analysis_draft=analysis_draft,
            council_settings=council_settings,
            selected_findings=selected_findings,
        )

        engine = self._build_engine(runtime_profile)
        try:
            result = await engine.execute(request)
        except Exception as exc:  # pragma: no cover - adapter/runtime failure path
            raise RuntimeError("Council deliberation failed") from exc

        self._raise_if_runtime_failed(result)

        return CouncilNote(
            status=result.status,
            question=request.question,
            participants=result.participants,
            rounds_completed=result.rounds_completed,
            summary=result.summary.consensus,
            key_agreements=result.summary.key_agreements,
            key_disagreements=result.summary.key_disagreements,
            final_recommendation=result.summary.final_recommendation,
            full_debate=[
                CouncilTranscriptEntry(
                    round=entry.round,
                    participant=entry.participant,
                    response=entry.response,
                    timestamp=entry.timestamp,
                )
                for entry in result.full_debate
            ],
            transcript_path=result.transcript_path or None,
        )
