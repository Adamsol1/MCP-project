import json
import logging
import re

from src.mcp_client.client import MCPClient
from src.models.analysis import AnalysisDraft, FindingModel, ProcessingResult
from src.models.confidence import (
    ConfidenceTier,
    FindingConfidence,
    PerspectiveAssertion,
)
from src.models.dialogue import Perspective
from src.services.confidence.assertion_enrichment import (
    enrich_assertions,
    validate_finding_ids,
)
from src.services.confidence.scoring import compute_confidence
from src.services.AI.gemini_agent import GeminiAgent

logger = logging.getLogger("app")

_DEFAULT_PERSPECTIVES = tuple(p.value for p in Perspective)


class AnalysisService:
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client

    async def generate_draft(
        self,
        processing_result: ProcessingResult,
        selected_perspectives: list[str] | None = None,
        pir: str = "",
    ) -> tuple[AnalysisDraft, ProcessingResult]:
        normalized = self._normalize_perspectives(selected_perspectives)
        enriched_result = self._enrich_findings(processing_result)
        fallback_draft = self._build_fallback_draft(enriched_result, normalized)
        findings_json = json.dumps(enriched_result.model_dump(), ensure_ascii=False)
        valid_ids = {f.id for f in enriched_result.findings}

        base_payload: dict | None = None
        merged_implications: dict = {}

        try:
            async with self.mcp_client.connect():
                for perspective in normalized:
                    persona = await self.mcp_client.read_resource(
                        f"knowledge://personas/{perspective}"
                    )
                    task_prompt = await self.mcp_client.get_prompt(
                        "analysis_generate",
                        {
                            "pir": pir,
                            "findings": findings_json,
                            "perspectives": perspective,
                        },
                    )
                    system_prompt = f"{persona}\n\n{task_prompt}"
                    agent = GeminiAgent(self.mcp_client)
                    raw = await agent.run(
                        system_prompt=system_prompt,
                        task=f"Generate an intelligence analysis from the {perspective} perspective.",
                        allowed_tool_names=set(),
                    )

                    try:
                        if isinstance(raw, str):
                            fence = re.search(
                                r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE
                            )
                            raw = fence.group(1).strip() if fence else raw.strip()
                        payload = json.loads(raw) if isinstance(raw, str) else raw
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(
                            "[AnalysisService] %s agent returned non-JSON — skipping.",
                            perspective,
                        )
                        continue

                    # First agent provides shared fields (title, summary, key_judgments, etc.)
                    if base_payload is None:
                        base_payload = payload

                    # Collect this perspective's implications
                    raw_assertions = payload.get(
                        "per_perspective_implications", {}
                    ).get(perspective, [])
                    if isinstance(raw_assertions, list):
                        raw_assertions = [
                            a
                            if isinstance(a, dict)
                            else {"assertion": str(a), "supporting_finding_ids": []}
                            for a in raw_assertions
                        ]
                        merged_implications[perspective] = validate_finding_ids(
                            raw_assertions, valid_ids
                        )

        except Exception:
            logger.warning(
                "[AnalysisService] MCP generation failed — using fallback draft.",
                exc_info=True,
            )
            return self._enrich_draft_assertions(
                fallback_draft, enriched_result
            ), enriched_result

        if base_payload is None:
            logger.warning(
                "[AnalysisService] No agents produced output — using fallback draft."
            )
            return self._enrich_draft_assertions(
                fallback_draft, enriched_result
            ), enriched_result

        base_payload["per_perspective_implications"] = merged_implications

        try:
            llm_draft = AnalysisDraft.model_validate(base_payload)
        except Exception:
            logger.warning(
                "[AnalysisService] Invalid draft payload — using fallback draft."
            )
            llm_draft = fallback_draft

        merged = self._merge_with_fallback(llm_draft, fallback_draft)
        filtered_implications = {
            k: v
            for k, v in merged.per_perspective_implications.items()
            if k in normalized
        }
        merged = merged.model_copy(
            update={"per_perspective_implications": filtered_implications}
        )
        return self._enrich_draft_assertions(merged, enriched_result), enriched_result

    def _enrich_findings(self, processing_result: ProcessingResult) -> ProcessingResult:
        enriched: list[FindingModel] = []
        for finding in processing_result.findings:
            source_urls = list(finding.supporting_data.get("source_refs", []))
            breakdown = compute_confidence(
                source_types=[finding.source],
                source_urls=source_urls or None,
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
            enriched.append(finding.model_copy(update={"computed_confidence": fc}))
        return ProcessingResult(findings=enriched, gaps=processing_result.gaps)

    def _enrich_draft_assertions(
        self,
        draft: AnalysisDraft,
        processing_result: ProcessingResult,
    ) -> AnalysisDraft:
        enriched_implications: dict[str, list[PerspectiveAssertion]] = {}
        for perspective, assertions in draft.per_perspective_implications.items():
            enriched_implications[perspective] = enrich_assertions(
                assertions, processing_result.findings
            )
        return draft.model_copy(
            update={"per_perspective_implications": enriched_implications}
        )

    def _normalize_perspectives(self, selected: list[str] | None) -> list[str]:
        if not selected:
            return list(_DEFAULT_PERSPECTIVES)
        normalized = [
            p.strip().lower()
            for p in selected
            if p.strip().lower() in _DEFAULT_PERSPECTIVES
        ]
        return normalized or list(_DEFAULT_PERSPECTIVES)

    def _build_fallback_draft(
        self,
        processing_result: ProcessingResult,
        selected_perspectives: list[str],
    ) -> AnalysisDraft:
        findings = processing_result.findings
        gaps = list(processing_result.gaps)
        first_id = findings[0].id if findings else None

        def _a(text: str, fids: list[str] | None = None) -> PerspectiveAssertion:
            return PerspectiveAssertion(
                assertion=text,
                supporting_finding_ids=fids or ([first_id] if first_id else []),
            )

        title_text = (
            "; ".join(f.title for f in findings[:4]) or "limited processed reporting"
        )
        first_gap = gaps[0] if gaps else "Attribution remains unresolved."

        all_implications: dict[str, list[PerspectiveAssertion]] = {
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
                    "The findings are directly relevant to Norwegian telecom and emergency communications operators."
                ),
                _a(
                    "Norwegian stakeholders should prioritize privileged-access review around network operations and identity services."
                ),
            ],
            "china": [
                _a(
                    "The infrastructure-overlap findings provide a comparative baseline for state-style telecom targeting without establishing attribution."
                ),
                _a(
                    f"From a China-focused lens, {first_gap.lower()} should limit any premature actor-specific conclusion."
                ),
            ],
            "eu": [
                _a(
                    "Cross-border telecom dependencies increase the regional significance of credential theft and vendor-access compromise."
                ),
                _a(
                    "EU-level coordination would be relevant if the access activity affects shared carriers or interconnection partners."
                ),
            ],
            "russia": [
                _a(
                    "The focus on Northern European telecom resilience intersects with regional critical-infrastructure threat scenarios."
                ),
                _a(f"The current record requires caution because {first_gap.lower()}"),
            ],
            "neutral": [
                _a(
                    "The findings support a cautious assessment of coordinated access development rather than isolated opportunistic events."
                ),
                _a(
                    "Available evidence is stronger on targeting patterns than on final intent or actor identity."
                ),
            ],
        }

        summary = (
            f"Analysis of {len(findings)} findings indicates a likely access-development campaign. "
            f"{len(gaps)} information gaps remain unresolved."
            if findings
            else f"No processed findings available. {len(gaps)} gaps remain open."
        )

        return AnalysisDraft(
            title="",
            summary=summary,
            key_judgments=[
                f"{f.title}: {f.why_it_matters} Confidence: {f.confidence}/100."
                for f in findings
            ]
            or ["No validated findings available to support a draft judgment."],
            per_perspective_implications={
                k: v for k, v in all_implications.items() if k in selected_perspectives
            },
            recommended_actions=[
                "Review findings and prioritize follow-up collection against unresolved gaps."
            ],
            information_gaps=gaps,
        )

    def _merge_with_fallback(
        self, llm_draft: AnalysisDraft, fallback: AnalysisDraft
    ) -> AnalysisDraft:
        merged_implications: dict[str, list[PerspectiveAssertion]] = {}
        for key in llm_draft.per_perspective_implications:
            llm_values = llm_draft.per_perspective_implications.get(key, [])
            merged_implications[key] = (
                llm_values or fallback.per_perspective_implications.get(key, [])
            )
        for key in fallback.per_perspective_implications:
            if key not in merged_implications:
                merged_implications[key] = fallback.per_perspective_implications[key]
        return AnalysisDraft(
            title=llm_draft.title.strip() if hasattr(llm_draft, "title") else "",
            summary=llm_draft.summary.strip() or fallback.summary,
            key_judgments=llm_draft.key_judgments or fallback.key_judgments,
            per_perspective_implications=merged_implications,
            recommended_actions=llm_draft.recommended_actions
            or fallback.recommended_actions,
            information_gaps=fallback.information_gaps,
        )
