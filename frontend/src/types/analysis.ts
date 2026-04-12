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
}

export interface ProcessingResult {
  findings: ProcessingFinding[];
  gaps: string[];
}

export interface AnalysisDraft {
  summary: string;
  key_judgments: string[];
  per_perspective_implications: Record<string, string[]>;
  recommended_actions: string[];
  information_gaps: string[];
}

export interface CouncilTranscriptEntry {
  round: number;
  participant: string;
  response: string;
  timestamp: string;
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

export interface AnalysisDraftResponse {
  processing_result: ProcessingResult;
  analysis_draft: AnalysisDraft;
  latest_council_note: CouncilNote | null;
  data_source: "session";
}

export interface RunAnalysisCouncilRequest {
  session_id: string;
  debate_point: string;
  finding_ids: string[];
  selected_perspectives: string[];
  council_settings?: CouncilRunSettings;
}
