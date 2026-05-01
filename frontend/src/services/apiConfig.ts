export const API_BACKEND_URL =
  import.meta.env.VITE_API_BACKEND_URL ??
  (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");
