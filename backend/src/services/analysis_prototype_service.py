"""Prototype service for building a draft analysis from processed findings."""

import logging

from src.models.analysis import AnalysisDraft, ProcessingResult
from src.models.dialogue import Perspective
from src.services.llm_service import LLMService

logger = logging.getLogger("app")


class AnalysisPrototypeService:
    """Generate an analysis draft from a ProcessingResult."""

    DEFAULT_PERSPECTIVES = tuple(p.value for p in Perspective)
    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService(model=self.DEFAULT_MODEL)

    async def generate_draft(
        self,
        processing_result: ProcessingResult,
        selected_perspectives: list[str] | None = None,
    ) -> AnalysisDraft:
        """Create an analysis draft grounded in processed findings."""
        normalized_perspectives = self._normalize_perspectives(selected_perspectives)
        fallback_draft = self._generate_fallback_draft(
            processing_result=processing_result,
            selected_perspectives=normalized_perspectives,
        )

        try:
            payload = await self.llm_service.generate_json(
                self._build_prompt(
                    processing_result=processing_result,
                    selected_perspectives=normalized_perspectives,
                )
            )
        except Exception as exc:  # pragma: no cover - network/runtime failure path
            logger.warning(
                "[AnalysisPrototypeService] Gemini draft generation failed, using fallback draft: %s",
                exc,
            )
            return fallback_draft

        try:
            llm_draft = AnalysisDraft.model_validate(payload)
        except Exception as exc:
            logger.warning(
                "[AnalysisPrototypeService] Gemini returned invalid draft payload, using fallback draft: %s",
                exc,
            )
            return fallback_draft

        return self._merge_with_fallback(
            llm_draft=llm_draft,
            fallback_draft=fallback_draft,
        )

    def _normalize_perspectives(
        self,
        selected_perspectives: list[str] | None,
    ) -> list[str]:
        if not selected_perspectives:
            return list(self.DEFAULT_PERSPECTIVES)

        normalized: list[str] = []
        seen: set[str] = set()
        for perspective in selected_perspectives:
            cleaned = perspective.strip().lower()
            if not cleaned or cleaned in seen or cleaned not in self.DEFAULT_PERSPECTIVES:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)

        if not normalized:
            return list(self.DEFAULT_PERSPECTIVES)
        return normalized

    def _build_prompt(
        self,
        processing_result: ProcessingResult,
        selected_perspectives: list[str],
    ) -> str:
        findings = processing_result.findings
        findings_text = "\n\n".join(
            "\n".join(
                [
                    f"{finding.id} | {finding.title}",
                    f"Finding: {finding.finding}",
                    f"Evidence summary: {finding.evidence_summary}",
                    f"Source: {finding.source}",
                    f"Confidence: {finding.confidence}/100",
                    f"Relevant PIRs: {', '.join(finding.relevant_to) if finding.relevant_to else 'None'}",
                    f"Why it matters: {finding.why_it_matters}",
                    f"Uncertainties: {'; '.join(finding.uncertainties) if finding.uncertainties else 'None'}",
                ]
            )
            for finding in findings
        )
        gaps_text = "\n".join(f"- {gap}" for gap in processing_result.gaps) or "- None"
        perspectives_text = ", ".join(selected_perspectives)

        return f"""
You are drafting an intelligence-analysis summary for an analyst UI.

Use the processed findings below as the primary evidence base.
Return only valid JSON matching this exact structure:
{{
  "summary": "string",
  "key_judgments": ["string"],
  "per_perspective_implications": {{
    "us": ["string"],
    "norway": ["string"],
    "china": ["string"],
    "eu": ["string"],
    "russia": ["string"],
    "neutral": ["string"]
  }},
  "recommended_actions": ["string"],
  "information_gaps": ["string"]
}}

Requirements:
- Be analytical, specific, and grounded in the findings.
- Do not mention being an AI.
- Summary must be 2-4 sentences.
- Key judgments must be distinct and substantive.
- For each perspective, provide 2 concise implications.
- Recommended actions should be actionable and analyst-relevant.
- information_gaps must reflect the provided gaps.
- Supported perspectives in this session: {perspectives_text}

Processed findings:
{findings_text}

Information gaps:
{gaps_text}
""".strip()

    def _generate_fallback_draft(
        self,
        processing_result: ProcessingResult,
        selected_perspectives: list[str],
    ) -> AnalysisDraft:
        findings = processing_result.findings
        gaps = list(processing_result.gaps)

        summary = self._build_summary(findings, gaps)
        key_judgments = self._build_key_judgments(findings)
        all_implications = self._build_perspective_implications(findings, gaps)
        per_perspective_implications = {
            key: all_implications[key]
            for key in self.DEFAULT_PERSPECTIVES
            if key in selected_perspectives
        }
        recommended_actions = self._build_recommended_actions(findings, gaps)

        return AnalysisDraft(
            summary=summary,
            key_judgments=key_judgments,
            per_perspective_implications=per_perspective_implications,
            recommended_actions=recommended_actions,
            information_gaps=gaps,
        )

    def _merge_with_fallback(
        self,
        llm_draft: AnalysisDraft,
        fallback_draft: AnalysisDraft,
    ) -> AnalysisDraft:
        merged_implications: dict[str, list[str]] = {}
        for key in self.DEFAULT_PERSPECTIVES:
            llm_values = llm_draft.per_perspective_implications.get(key, [])
            merged_implications[key] = llm_values or fallback_draft.per_perspective_implications.get(
                key, []
            )

        return AnalysisDraft(
            summary=llm_draft.summary.strip() or fallback_draft.summary,
            key_judgments=llm_draft.key_judgments or fallback_draft.key_judgments,
            per_perspective_implications=merged_implications,
            recommended_actions=llm_draft.recommended_actions
            or fallback_draft.recommended_actions,
            information_gaps=fallback_draft.information_gaps,
        )

    def _build_summary(self, findings, gaps: list[str]) -> str:
        if not findings:
            return (
                "Prototype analysis found no processed findings to assess. "
                f"{len(gaps)} information gaps remain open."
            )

        top_titles = ", ".join(f.title for f in findings[:3])
        return (
            f"Analysis of {len(findings)} processed findings indicates a likely access-development "
            "campaign against Northern European telecom and critical infrastructure functions. "
            f"The strongest signals combine {top_titles}. "
            f"{len(gaps)} information gaps remain unresolved."
        )

    def _build_key_judgments(self, findings) -> list[str]:
        if not findings:
            return ["No validated findings were available to support a draft judgment."]

        judgments = []
        for finding in findings:
            judgments.append(
                f"{finding.title}: {finding.why_it_matters} Confidence remains {finding.confidence}/100."
            )
        return judgments

    def _build_perspective_implications(
        self, findings, gaps: list[str]
    ) -> dict[str, list[str]]:
        titles = [finding.title for finding in findings]
        title_text = "; ".join(titles[:4]) if titles else "limited processed reporting"
        first_gap = gaps[0] if gaps else "Attribution remains unresolved."

        return {
            "us": [
                "The combination of credential-access activity and phishing staging is relevant to allied telecom providers and shared vendor-access pathways.",
                f"US analysts should track whether the pattern seen in {title_text} reflects a reusable access-development model against critical infrastructure.",
            ],
            "norway": [
                "The findings are directly relevant to Norwegian telecom and emergency communications operators because the scenario centers on Northern European resilience functions.",
                "Norwegian stakeholders should prioritize privileged-access review around network operations, identity services, and trusted third-party connectivity.",
            ],
            "china": [
                "The infrastructure-overlap and campaign-intent findings provide a comparative baseline for state-style telecom targeting without establishing attribution.",
                f"From a China-focused analytical lens, {first_gap.lower()} should limit any premature actor-specific conclusion.",
            ],
            "eu": [
                "Cross-border telecom dependencies increase the regional significance of credential theft, phishing staging, and vendor-access compromise.",
                "EU-level coordination would be relevant if the observed access activity affects shared carriers, interconnection partners, or continuity planning.",
            ],
            "russia": [
                "The focus on Northern European telecom resilience and subsea or interconnection-adjacent functions intersects with regional critical-infrastructure threat scenarios often assessed in relation to Russia.",
                f"The current record still requires caution because {first_gap.lower()}",
            ],
            "neutral": [
                "Taken together, the findings support a cautious assessment of coordinated access development rather than isolated opportunistic events.",
                "The available evidence is stronger on targeting patterns and access preparation than on final intent or actor identity.",
            ],
        }

    def _build_recommended_actions(self, findings, gaps: list[str]) -> list[str]:
        actions = []
        finding_text = " ".join(
            f"{finding.title} {finding.finding} {finding.why_it_matters}"
            for finding in findings
        ).lower()

        if "credential" in finding_text or "login" in finding_text:
            actions.append(
                "Review privileged telecom administration accounts for anomalous logins, mailbox-rule changes, and federation activity."
            )
        if "domain" in finding_text or "phish" in finding_text:
            actions.append(
                "Block and monitor lookalike domains, related URLs, and hosting infrastructure associated with staged phishing activity."
            )
        if "infrastructure" in finding_text or "tooling" in finding_text or "malware" in finding_text:
            actions.append(
                "Correlate observed IOCs and historical cases to determine whether infrastructure reuse reflects a repeatable intrusion playbook."
            )
        if "targeting" in finding_text or "campaign" in finding_text:
            actions.append(
                "Confirm victimology across telecom, interconnection, and managed-access partners to determine whether targeting has expanded regionally."
            )

        if not actions:
            actions.append(
                "Review processed findings and supporting data to prioritize follow-up collection and containment."
            )

        if gaps:
            actions.append(
                "Task follow-up collection against unresolved attribution, victimology, and intent gaps before making stronger campaign assessments."
            )

        return actions
