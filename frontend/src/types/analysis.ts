// ---------------------------------------------------------------------------
// Shared confidence types
// ---------------------------------------------------------------------------

/// Represents the different confidence tiers that can be assigned to findings and assertions,
/// based on their assessed reliability and credibility.
export type ConfidenceTier = "low" | "moderate" | "high" | "assessed";


/**
 * The confidence level of a particular finding, including its tier (e.g., low, moderate, high, assessed),
 * a numerical score, and the contributing factors such as authority, corroboration, independence, circularity,
 * and the types of sources that support it.
 */
export interface FindingConfidence {
  tier: ConfidenceTier;
  score: number;
  authority: number;
  corroboration: number;
  independence: number;
  circular_flag: boolean;
  source_types: string[];
}

/**
 * The confidence level of a particular assertion, including its tier (e.g., low, moderate, high, assessed),
 * a numerical score, and the contributing factors such as authority, corroboration, independence, circularity,
 * and the types of sources that support it.
 */
export interface AssertionConfidence {
  tier: ConfidenceTier;
  score: number;
  authority: number;
  corroboration: number;
  independence: number;
  circular_flag: boolean;
}

/**
 * Represents an assertion related to a particular perspective, including the assertion text, optional analysis,
 * the IDs of the findings that support this assertion, the types of sources that support it, and its confidence level.
 * This structure is used to organize the AI's key judgments and their supporting evidence in a way that is transparent
 * and traceable back to the underlying data.
 */
export interface PerspectiveAssertion {
  assertion: string;
  analysis?: string;
  supporting_finding_ids: string[];
  source_types: string[];
  confidence: AssertionConfidence | null;
}

// ---------------------------------------------------------------------------
// Collection Coverage (post-collection)
// ---------------------------------------------------------------------------

/**
 * A reference to a finding within the coverage analysis, including its ID, title, and source.
 */
export interface CoverageFindingRef {
  id: string;
  title: string;
  source: string;
}

/**
 * Represents the coverage score for a specific PIR question, including its index, text, priority level, confidence tier,
 * numerical score, the count of findings that address this PIR, the types of sources that contribute to this coverage,
 * a flag indicating whether there are any identified gaps in coverage, the rationale behind the score, and references to the specific findings.
 * This structure is used to provide a detailed breakdown of how well the collected information addresses each PIR question.
 */
export interface PirCoverageScore {
  pir_index: number;
  pir_question: string;
  priority: string;
  tier: ConfidenceTier;
  score: number;
  finding_count: number;
  source_types: string[];
  has_gap_flag: boolean;
  rationale: string;
  findings: CoverageFindingRef[];
}

/**
 * Represents the overall coverage analysis results after the collection phase, including the coverage scores for each PIR question,
 * the aggregate confidence tier and numerical score for the entire collection, and a summary of the coverage assessment.
 */
export interface CollectionCoverageResult {
  per_pir: PirCoverageScore[];
  aggregate_tier: ConfidenceTier;
  aggregate_score: number;
  summary: string;
}

// ---------------------------------------------------------------------------
// Processing & Analysis
// ---------------------------------------------------------------------------


export interface CouncilRunSettings {
  mode: "conference" | "quick";
  rounds: number;
  timeout_seconds: number;
  vote_retry_enabled: boolean;
  vote_retry_attempts: number;
}

/**
 * Represents a single finding extracted during the processing phase, including its ID, title, detailed finding text,
 * a summary of the evidence supporting it, the source of the finding, an assessed confidence score, the specific aspects it is relevant to,
 * any identified uncertainties, and an explanation of why this finding matters in the context of the overall analysis. Findings may also include
 * optional supporting data such as extracted entities, timestamps, locations, knowledge base references, attack IDs, domains, source URLs, source references, and indicators of compromise (IOCs).
 */
export interface ProcessingFinding {
  id: string;
  title: string;
  finding: string;
  evidence_summary: string;
  source: string;
  confidence: number;
  relevant_to: string[];
  supporting_data: Record<string, string[]>;
  why_it_matters: string;
  uncertainties: string[];
  computed_confidence: FindingConfidence | null;
}

export interface ProcessingResult {
  findings: ProcessingFinding[];
  gaps: string[];
}

/**
 * Represents the structured analysis generated during the analysis phase, including an overall title and summary,
 * a list of key judgments, a mapping of perspectives to their related assertions, a list of recommended actions based on the analysis,
 * and any identified information gaps that may require further investigation.
 */
export interface Analysis {
  title: string;
  summary: string;
  key_judgments: string[];
  per_perspective_implications: Record<string, PerspectiveAssertion[]>;
  recommended_actions: string[];
  information_gaps: string[];
}

/**
 * Represents the response from the analysis endpoint, including the processing results, the drafted analysis,
 * the latest council note if applicable,
 */
export interface CouncilTranscriptEntry {
  round: number;
  participant: string;
  response: string;
  timestamp: string;
  summary?: string;
}

export interface CouncilNote {
  status: string;
  question: string;
  participants: string[];
  rounds_completed: number;
  summary: string;
  key_agreements: string[];
  key_disagreements: string[];
  final_recommendation: string;
  full_debate: CouncilTranscriptEntry[];
  transcript_path: string | null;
}

export interface AnalysisResponse {
  processing_result: ProcessingResult;
  analysis_draft: Analysis;
  latest_council_note: CouncilNote | null;
  collection_coverage: CollectionCoverageResult | null;
  data_source: "session";
}

export interface RunAnalysisCouncilRequest {
  session_id: string;
  debate_point: string;
  finding_ids: string[];
  selected_perspectives: string[];
  council_settings?: CouncilRunSettings;
}
