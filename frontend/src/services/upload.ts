import axios from 'axios';

/** Base URL for the backend REST API. */
const API_BACKEND_URL = 'http://localhost:8000';

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
 * @returns The backend response data (upload confirmation / metadata).
 */
export async function uploadFile(file: File){

  const formData = new FormData();
  formData.append('file', file);

  const httpResponse = await axios.post(
    `${API_BACKEND_URL}/api/import/upload`,
    formData
  );

  return httpResponse.data;

}
