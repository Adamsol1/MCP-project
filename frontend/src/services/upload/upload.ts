import axios from "axios";
import { API_BACKEND_URL } from "../apiConfig";

/** User-supplied bibliographic metadata attached to an uploaded file. */
export interface CitationMetadata {
  author: string;
  year: string;
  title: string;
  publisher: string;
}

/** Full backend record for a file that has been uploaded to a session. */
export interface UploadedFileRecord {
  file_upload_id: string;
  session_id: string;
  original_filename: string;
  /** Sanitised filename stored on disk (may differ from `original_filename`). */
  filename: string;
  stored_filename: string;
  stored_path: string;
  extension: string;
  mime_type?: string | null;
  size_bytes: number;
  uploaded_at: string;
  /** Backend parse pipeline state: `ready` means text was extracted and is search-indexable. */
  parse_status: "pending" | "ready" | "failed" | "skipped";
  searchable: boolean;
  /** Human-readable reason the file was excluded from search (e.g. unsupported format). */
  search_skip_reason?: string | null;
  /** Path to the extracted Markdown representation of the file; null if parsing hasn't run. */
  parsed_markdown_path?: string | null;
  citation?: CitationMetadata;
}

/** Backend response for a successful single-file upload — extends the record with a status discriminant. */
export interface UploadResponse extends UploadedFileRecord {
  status: "success";
}

/** Backend response shape for the list-files endpoint. */
interface UploadListResponse {
  status: "success";
  session_id: string;
  files: UploadedFileRecord[];
}

/**
 * Uploads a single file to the backend import endpoint.
 *
 * The file is sent as multipart/form-data so the backend receives a proper
 * file object rather than a raw binary body. Axios sets the Content-Type
 * header automatically when given a FormData instance, including the correct
 * boundary string required for multipart parsing on the server.
 *
 * @param file - The File object selected by the user (from an input element
 *               or a drag-and-drop event).
 * @param sessionId - Backend dialogue session ID used to scope uploads.
 * @returns The backend response data (upload confirmation / metadata).
 */
export async function uploadFile(
  file: File,
  sessionId: string,
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("session_id", sessionId);

  const httpResponse = await axios.post<UploadResponse>(
    `${API_BACKEND_URL}/api/import/upload`,
    formData,
  );

  return httpResponse.data;
}

/**
 * Fetches all files that have been uploaded under a given session.
 *
 * @param sessionId - Backend session ID whose uploaded files to list.
 * @returns Array of file records (may be empty if no files have been uploaded yet).
 */
export async function listUploadedFiles(
  sessionId: string,
): Promise<UploadedFileRecord[]> {
  const httpResponse = await axios.get<UploadListResponse>(
    `${API_BACKEND_URL}/api/import/files`,
    { params: { session_id: sessionId } },
  );
  return httpResponse.data.files;
}

/**
 * Deletes a single uploaded file from the backend.
 *
 * @param sessionId    - Session the file belongs to.
 * @param fileUploadId - The `file_upload_id` of the record to remove.
 */
export async function deleteUploadedFile(
  sessionId: string,
  fileUploadId: string,
): Promise<void> {
  await axios.delete(`${API_BACKEND_URL}/api/import/files/${fileUploadId}`, {
    params: { session_id: sessionId },
  });
}

/**
 * Delete all backend and MCP artifacts for a session.
 *
 * Tolerates 404 (session never reached the backend) so brand-new conversations
 * can be removed without noise.  All other errors propagate so the caller can
 * surface them to the user — silently swallowing them used to hide real
 * failures where the DB row stayed behind.
 */
export async function deleteSessionArtifacts(sessionId: string): Promise<void> {
  try {
    await axios.delete(`${API_BACKEND_URL}/api/sessions/${sessionId}`);
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 404) {
      return;
    }
    throw err;
  }
}
