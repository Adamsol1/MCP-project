import axios from "axios";
import type {
  CouncilNote,
  RunAnalysisCouncilRequest,
} from "../../types/analysis";
import { API_BACKEND_URL } from "../apiConfig";

const ANALYSIS_COUNCIL_TIMEOUT_MS = 15 * 60 * 1000;

/**
 * Submits a council analysis request to the backend and returns the resulting note.
 *
 * A council run takes a set of findings and perspectives and has multiple AI
 * agents debate them, producing a consolidated `CouncilNote` with their verdict.
 *
 * @param request - The full council run configuration (findings, perspectives, settings).
 * @returns The `CouncilNote` produced by the council debate.
 */
export async function runAnalysisCouncil(request: RunAnalysisCouncilRequest) {
  const httpResponse = await axios.post<CouncilNote>(
    `${API_BACKEND_URL}/api/analysis/council`,
    request,
    { timeout: ANALYSIS_COUNCIL_TIMEOUT_MS },
  );

  return httpResponse.data;
}
