"""Analysis-stage council wrapper using app runtime defaults."""

import logging
import os
from pathlib import Path  # used in __init__ for working_directory

from src.mcp_client.client import MCPClient
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

logger = logging.getLogger("app")

_COUNCIL_MCP_URL = os.getenv("COUNCIL_MCP_URL", "http://127.0.0.1:8003/sse")


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

    def __init__(self, working_directory: str | Path | None = None, mcp_client: MCPClient | None = None):
        if working_directory is None:
            working_directory = (
                Path(__file__).resolve().parents[2] / "data" / "outputs"
            )
        self.working_directory = Path(working_directory)
        self.working_directory.mkdir(parents=True, exist_ok=True)
        self.transcript_dir = self.working_directory / "council_transcripts"
        self.transcript_dir.mkdir(parents=True, exist_ok=True)
        self.mcp_client = mcp_client or MCPClient(server_url=_COUNCIL_MCP_URL)

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

    def build_participants(self, selected_perspectives: list[str]) -> list[dict]:
        normalized = self._normalize_perspectives(selected_perspectives)
        if len(normalized) < 2:
            raise ValueError("At least 2 perspectives are required for council deliberation")

        participants = []
        for perspective in normalized:
            persona = get_council_persona(perspective)
            participants.append({
                "cli": self.DEFAULT_ADAPTER,
                "model": self.DEFAULT_MODEL,
                "display_name": persona.display_name,
                "persona_prompt": persona.persona_prompt,
            })
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
    ) -> dict:
        runtime_profile = self.resolve_runtime_profile(council_settings)
        participants = self.build_participants(selected_perspectives)
        question = self.build_question(debate_point, selected_findings or [])
        context = self.build_context(
            processing_result=processing_result,
            analysis_draft=analysis_draft,
            debate_point=debate_point,
            selected_findings=selected_findings,
        )

        return {
            "question": question,
            "participants": participants,
            "rounds": runtime_profile.rounds,
            "mode": runtime_profile.mode,
            "context": context,
            "working_directory": runtime_profile.working_directory,
        }

    def _raise_if_runtime_failed(self, result: dict) -> None:
        debates = result.get("full_debate", [])
        if not debates:
            raise RuntimeError("Council runtime failed: no participant responses were produced")

        if any(not entry.get("response", "").startswith("[ERROR:") for entry in debates):
            return

        first_error = debates[0].get("response", "").strip("[]")
        if "API key" in first_error or "api key" in first_error:
            raise RuntimeError(
                "Council runtime failed: Gemini API access is not configured correctly."
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
        selected_findings = (
            [f for f in processing_result.findings if f.id in finding_ids]
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

        logger.info(f"[CouncilService] Calling deliberate tool via MCP at {_COUNCIL_MCP_URL}")
        async with self.mcp_client.connect():
            result = await self.mcp_client.call_tool("deliberate", request)

        if not isinstance(result, dict):
            raise RuntimeError(f"Unexpected response type from deliberate tool: {type(result)}")
        if result.get("status") == "failed" or "error" in result:
            raise RuntimeError(f"Council deliberation failed: {result.get('error', 'unknown error')}")

        self._raise_if_runtime_failed(result)

        return CouncilNote(
            status=result.get("status", "completed"),
            question=request["question"],
            participants=result.get("participants", []),
            rounds_completed=result.get("rounds_completed", 0),
            summary=result.get("summary", {}).get("consensus", ""),
            key_agreements=result.get("summary", {}).get("key_agreements", []),
            key_disagreements=result.get("summary", {}).get("key_disagreements", []),
            final_recommendation=result.get("summary", {}).get("final_recommendation", ""),
            full_debate=[
                CouncilTranscriptEntry(
                    round=entry["round"],
                    participant=entry["participant"],
                    response=entry["response"],
                    timestamp=entry.get("timestamp", ""),
                )
                for entry in result.get("full_debate", [])
            ],
            transcript_path=result.get("transcript_path") or None,
        )
