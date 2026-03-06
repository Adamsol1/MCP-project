import { http, HttpResponse } from "msw";

export const handlers = [
  http.post("/api/import/upload", async ({ request }) => {
    const body = await request.formData();
    const uploadedFile = body.get("file");
    const sessionId = body.get("session_id");

    const filename =
      uploadedFile instanceof File ? uploadedFile.name : "test.txt";
    return HttpResponse.json({
      status: "success",
      file_upload_id: "upload-test-1",
      session_id: typeof sessionId === "string" ? sessionId : "session-test",
      original_filename: filename,
      filename,
      stored_filename: `upload-test-1__${filename}`,
      stored_path: `/uploads/${filename}`,
      extension: `.${filename.split(".").pop() ?? "txt"}`,
      size_bytes: uploadedFile instanceof File ? uploadedFile.size : 0,
      uploaded_at: "2026-03-06T10:00:00Z",
      parse_status: "ready",
      searchable: true,
      citation: {
        author: "Unknown",
        year: "Unknown",
        title: filename,
        publisher: "Unknown",
      },
    });
  }),
  http.get("/api/import/files", () => {
    return HttpResponse.json({
      status: "success",
      session_id: "session-test",
      files: [],
    });
  }),
  http.delete("/api/import/files/:fileUploadId", () => {
    return new HttpResponse(null, { status: 204 });
  }),
];

