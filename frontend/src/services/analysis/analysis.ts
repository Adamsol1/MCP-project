import axios from "axios";
import type {
  CouncilNote,
  RunAnalysisCouncilRequest,
} from "../../types/analysis";
import { API_BACKEND_URL } from "../apiConfig";

export async function runAnalysisCouncil(request: RunAnalysisCouncilRequest) {
  const httpResponse = await axios.post<CouncilNote>(
    `${API_BACKEND_URL}/api/analysis/council`,
    request,
  );

  return httpResponse.data;
}
