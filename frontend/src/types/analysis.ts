// ---------------------------------------------------------------------------
// Shared confidence types
// ---------------------------------------------------------------------------

export type ConfidenceTier = "low" | "moderate" | "high" | "assessed";

export interface FindingConfidence {
  tier: ConfidenceTier;
  score: number;
  authority: number;
  corroboration: number;
  independence: number;
  circular_flag: boolean;
  source_types: string[];
}

export interface AssertionConfidence {
  tier: ConfidenceTier;
  score: number;
  authority: number;
  corroboration: number;
  independence: number;
  circular_flag: boolean;
}

export interface PerspectiveAssertion {
  assertion: string;
  supporting_finding_ids: string[];
  source_types: string[];
  confidence: AssertionConfidence | null;
}

// ---------------------------------------------------------------------------
// Collection Coverage (post-collection)
// ---------------------------------------------------------------------------

export interface CoverageFindingRef {
  id: string;
  title: string;
  source: string;
}

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

export interface Analysis {
  title: string;
  summary: string;
  key_judgments: string[];
  per_perspective_implications: Record<string, PerspectiveAssertion[]>;
  recommended_actions: string[];
  information_gaps: string[];
}

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
