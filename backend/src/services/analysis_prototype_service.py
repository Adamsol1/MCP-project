"""Prototype service for building a draft analysis from processed findings."""

import logging

from src.models.analysis import AnalysisDraft, FindingModel, ProcessingResult
from src.models.confidence import (
    ConfidenceTier,
    FindingConfidence,
    PerspectiveAssertion,
)
from src.models.dialogue import Perspective
from src.services.confidence.assertion_enrichment import enrich_assertions, validate_finding_ids
from src.services.confidence.scoring import compute_confidence
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
    ) -> tuple[AnalysisDraft, ProcessingResult]:
        """Create an analysis draft grounded in processed findings.

        Returns:
            (AnalysisDraft, ProcessingResult) — the draft has per-assertion
            confidence attached; the ProcessingResult has computed_confidence
            on each FindingModel.
        """
        normalized_perspectives = self._normalize_perspectives(selected_perspectives)

        # Layer 2: compute finding-level confidence before generating the draft
        enriched_processing_result = self._enrich_findings(processing_result)

        fallback_draft = self._generate_fallback_draft(
            processing_result=enriched_processing_result,
            selected_perspectives=normalized_perspectives,
        )

        try:
            payload = await self.llm_service.generate_json(
                self._build_prompt(
                    processing_result=enriched_processing_result,
                    selected_perspectives=normalized_perspectives,
                )
            )
        except Exception as exc:  # pragma: no cover - network/runtime failure path
            logger.warning(
                "[AnalysisPrototypeService] Gemini draft generation failed, using fallback draft: %s",
                exc,
            )
            return fallback_draft, enriched_processing_result

        # Validate and strip hallucinated finding IDs before model parsing
        valid_ids = {f.id for f in enriched_processing_result.findings}
        raw_implications = payload.get("per_perspective_implications", {})
        for perspective_key, assertion_list in raw_implications.items():
            if isinstance(assertion_list, list):
                raw_assertions = [
                    a if isinstance(a, dict) else {"assertion": str(a), "supporting_finding_ids": []}
                    for a in assertion_list
                ]
                raw_implications[perspective_key] = validate_finding_ids(raw_assertions, valid_ids)
        payload["per_perspective_implications"] = raw_implications

        try:
            llm_draft = AnalysisDraft.model_validate(payload)
        except Exception as exc:
            logger.warning(
                "[AnalysisPrototypeService] Gemini returned invalid draft payload, using fallback draft: %s",
                exc,
            )
            return fallback_draft, enriched_processing_result

        merged = self._merge_with_fallback(
            llm_draft=llm_draft,
            fallback_draft=fallback_draft,
        )

        # Enforce: only return implications for the selected perspectives
        filtered_implications = {
            k: v for k, v in merged.per_perspective_implications.items()
            if k in normalized_perspectives
        }
        merged = merged.model_copy(update={"per_perspective_implications": filtered_implications})

        # Layer 3: compute assertion-level confidence for each perspective
        enriched_draft = self._enrich_draft_assertions(merged, enriched_processing_result)
        return enriched_draft, enriched_processing_result

    # ------------------------------------------------------------------
    # Finding-level confidence (Layer 2)
    # ------------------------------------------------------------------

    def _enrich_findings(self, processing_result: ProcessingResult) -> ProcessingResult:
        """Return a new ProcessingResult where each finding has computed_confidence set."""
        enriched_findings: list[FindingModel] = []
        for finding in processing_result.findings:
            source_types = [finding.source]
            source_urls = list(finding.supporting_data.get("source_refs", []))
            breakdown = compute_confidence(
                source_types=source_types,
                source_urls=source_urls if source_urls else None,
            )
            fc = FindingConfidence(
                tier=ConfidenceTier(breakdown.tier),
                score=breakdown.raw_score,
                authority=round(breakdown.authority, 4),
                corroboration=round(breakdown.corroboration, 4),
                independence=round(breakdown.independence, 4),
                circular_flag=breakdown.circular_flag,
                source_types=breakdown.source_types,
            )
            enriched_findings.append(finding.model_copy(update={"computed_confidence": fc}))
        return ProcessingResult(
            findings=enriched_findings,
            gaps=processing_result.gaps,
        )

    # ------------------------------------------------------------------
    # Assertion-level confidence (Layer 3)
    # ------------------------------------------------------------------

    def _enrich_draft_assertions(
        self,
        draft: AnalysisDraft,
        processing_result: ProcessingResult,
    ) -> AnalysisDraft:
        """Attach AssertionConfidence to every PerspectiveAssertion in the draft."""
        enriched_implications: dict[str, list[PerspectiveAssertion]] = {}
        for perspective, assertions in draft.per_perspective_implications.items():
            enriched_implications[perspective] = enrich_assertions(
                assertions, processing_result.findings
            )
        return draft.model_copy(update={"per_perspective_implications": enriched_implications})

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

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
        finding_ids_list = ", ".join(f.id for f in findings) or "none"

        return f"""
You are drafting an intelligence-analysis summary for an analyst UI.

Use the processed findings below as the primary evidence base.
Return only valid JSON matching this exact structure:
{{
  "title": "string — 6-10 word concise intelligence assessment title",
  "summary": "string",
  "key_judgments": ["string"],
  "per_perspective_implications": {{
    "us": [
      {{
        "assertion": "string — analytical implication",
        "supporting_finding_ids": ["F-001"]
      }}
    ]
  }},
  "recommended_actions": ["string"],
  "information_gaps": ["string"]
}}

Requirements:
- Be analytical, specific, and grounded in the findings.
- Do not mention being an AI.
- Title must be 6-10 words, intelligence-report style (e.g. "China-Taiwan Conflict Probability Assessment Q2 2025").
- Summary must be 2-4 sentences.
- Key judgments must be distinct and substantive.
- Only generate per_perspective_implications for these perspectives: {perspectives_text}
- For each perspective, provide 2 concise implications as objects with "assertion" and "supporting_finding_ids".
- supporting_finding_ids must only contain IDs from this list: {finding_ids_list}
- If an implication is not directly traceable to a specific finding, use an empty array [].
- Recommended actions should be actionable and analyst-relevant.
- information_gaps must reflect the provided gaps.

Processed findings:
{findings_text}

Information gaps:
{gaps_text}
""".strip()

    # ------------------------------------------------------------------
    # Fallback draft generation (no LLM)
    # ------------------------------------------------------------------

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
            title="",
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
        merged_implications: dict[str, list[PerspectiveAssertion]] = {}
        for key in llm_draft.per_perspective_implications:
            llm_values = llm_draft.per_perspective_implications.get(key, [])
            merged_implications[key] = llm_values or fallback_draft.per_perspective_implications.get(
                key, []
            )
        # Include any fallback keys not returned by LLM
        for key in fallback_draft.per_perspective_implications:
            if key not in merged_implications:
                merged_implications[key] = fallback_draft.per_perspective_implications[key]

        return AnalysisDraft(
            title=llm_draft.title.strip() or fallback_draft.title,
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
    ) -> dict[str, list[PerspectiveAssertion]]:
        """Build fallback implications as PerspectiveAssertion objects.

        Uses the first finding's ID where possible to seed supporting_finding_ids.
        Confidence will be computed by the enrichment pass.
        """
        first_id = findings[0].id if findings else None
        titles = [finding.title for finding in findings]
        title_text = "; ".join(titles[:4]) if titles else "limited processed reporting"
        first_gap = gaps[0] if gaps else "Attribution remains unresolved."

        def _a(text: str, fids: list[str] | None = None) -> PerspectiveAssertion:
            return PerspectiveAssertion(
                assertion=text,
                supporting_finding_ids=fids or ([first_id] if first_id else []),
            )

        return {
            "us": [
                _a(
                    "The combination of credential-access activity and phishing staging is relevant to allied telecom providers and shared vendor-access pathways."
                ),
                _a(
                    f"US analysts should track whether the pattern seen in {title_text} reflects a reusable access-development model against critical infrastructure."
                ),
            ],
            "norway": [
                _a(
                    "The findings are directly relevant to Norwegian telecom and emergency communications operators because the scenario centers on Northern European resilience functions."
                ),
                _a(
                    "Norwegian stakeholders should prioritize privileged-access review around network operations, identity services, and trusted third-party connectivity."
                ),
            ],
            "china": [
                _a(
                    "The infrastructure-overlap and campaign-intent findings provide a comparative baseline for state-style telecom targeting without establishing attribution."
                ),
                _a(
                    f"From a China-focused analytical lens, {first_gap.lower()} should limit any premature actor-specific conclusion."
                ),
            ],
            "eu": [
                _a(
                    "Cross-border telecom dependencies increase the regional significance of credential theft, phishing staging, and vendor-access compromise."
                ),
                _a(
                    "EU-level coordination would be relevant if the observed access activity affects shared carriers, interconnection partners, or continuity planning."
                ),
            ],
            "russia": [
                _a(
                    "The focus on Northern European telecom resilience and subsea or interconnection-adjacent functions intersects with regional critical-infrastructure threat scenarios often assessed in relation to Russia."
                ),
                _a(
                    f"The current record still requires caution because {first_gap.lower()}"
                ),
            ],
            "neutral": [
                _a(
                    "Taken together, the findings support a cautious assessment of coordinated access development rather than isolated opportunistic events."
                ),
                _a(
                    "The available evidence is stronger on targeting patterns and access preparation than on final intent or actor identity."
                ),
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
