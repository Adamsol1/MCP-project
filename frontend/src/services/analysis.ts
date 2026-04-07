import axios from "axios";
import type {
  AnalysisDraftResponse,
  CouncilNote,
  RunAnalysisCouncilRequest,
} from "../types/analysis";

const API_BACKEND_URL = "http://localhost:8000";

export interface GetAnalysisDraftOptions {
  forceRefresh?: boolean;
  demoDataset?: string;
}

export async function getAnalysisDraft(
  sessionId: string,
  options: GetAnalysisDraftOptions = {},
) {
  const httpResponse = await axios.post<AnalysisDraftResponse>(
    `${API_BACKEND_URL}/api/analysis/draft`,
    {
      session_id: sessionId,
      force_refresh: options.forceRefresh ?? false,
      demo_dataset: options.demoDataset,
    },
  );

  return httpResponse.data;
}

export async function runAnalysisCouncil(
  request: RunAnalysisCouncilRequest,
) {
  const httpResponse = await axios.post<CouncilNote>(
    `${API_BACKEND_URL}/api/analysis/council`,
    request,
  );

  return httpResponse.data;
}
