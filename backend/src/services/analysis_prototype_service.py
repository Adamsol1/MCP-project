"""Prototype service for building a draft analysis from processed findings."""

from src.models.analysis import AnalysisDraft, ProcessingResult
from src.models.dialogue import Perspective


class AnalysisPrototypeService:
    """Generate a deterministic analysis draft from a ProcessingResult."""

    DEFAULT_PERSPECTIVES = tuple(p.value for p in Perspective)

    def generate_draft(
        self,
        processing_result: ProcessingResult,
        selected_perspectives: list[str] | None = None,
    ) -> AnalysisDraft:
        """Create a prototype analysis draft grounded in processed findings."""
        del selected_perspectives

        findings = processing_result.findings
        gaps = list(processing_result.gaps)

        summary = self._build_summary(findings, gaps)
        key_judgments = self._build_key_judgments(findings)
        per_perspective_implications = self._build_perspective_implications(
            findings, gaps
        )
        recommended_actions = self._build_recommended_actions(findings, gaps)

        return AnalysisDraft(
            summary=summary,
            key_judgments=key_judgments,
            per_perspective_implications=per_perspective_implications,
            recommended_actions=recommended_actions,
            information_gaps=gaps,
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
