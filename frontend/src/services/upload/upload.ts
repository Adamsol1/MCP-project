import axios from "axios";
import { API_BACKEND_URL } from "../apiConfig";

export interface CitationMetadata {
  author: string;
  year: string;
  title: string;
  publisher: string;
}

export interface UploadedFileRecord {
  file_upload_id: string;
  session_id: string;
  original_filename: string;
  filename: string;
  stored_filename: string;
  stored_path: string;
  extension: string;
  mime_type?: string | null;
  size_bytes: number;
  uploaded_at: string;
  parse_status: "pending" | "ready" | "failed" | "skipped";
  searchable: boolean;
  search_skip_reason?: string | null;
  parsed_markdown_path?: string | null;
  citation?: CitationMetadata;
}

export interface UploadResponse extends UploadedFileRecord {
  status: "success";
}

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

/** Fetch all uploads stored for a session. */
export async function listUploadedFiles(
  sessionId: string,
): Promise<UploadedFileRecord[]> {
  const httpResponse = await axios.get<UploadListResponse>(
    `${API_BACKEND_URL}/api/import/files`,
    { params: { session_id: sessionId } },
  );
  return httpResponse.data.files;
}

/** Delete one uploaded file by upload id in a session. */
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
 * Silently succeeds if the session has no artifacts (new session that never
 * reached the backend). Errors are swallowed so the frontend conversation can
 * still be removed from localStorage even if the backend is unreachable.
 */
export async function deleteSessionArtifacts(sessionId: string): Promise<void> {
  try {
    await axios.delete(`${API_BACKEND_URL}/api/sessions/${sessionId}`);
  } catch {
    // Best-effort: don't block the frontend deletion if the backend is down
    // or the session never had any artifacts.
  }
}
