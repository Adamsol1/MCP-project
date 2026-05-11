/** Base URL for all backend API requests. Falls back to localhost for local dev when the env var is unset. */
export const API_BACKEND_URL =
  import.meta.env.VITE_API_BACKEND_URL ??
  (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");
