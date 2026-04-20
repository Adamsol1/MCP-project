/**
 * upload service tests.
 *
 * All axios calls are mocked so no real HTTP requests are made.
 * Coverage includes:
 *  - uploadFile: multipart form construction and happy path
 *  - listUploadedFiles: query param and response unwrapping
 *  - deleteUploadedFile: URL construction and query param
 *  - deleteSessionArtifacts: happy path and silent failure on error
 *
 * Run with: cd frontend && npx vitest upload.test
 */

import axios from "axios";
import { describe, expect, it, vi, beforeEach } from "vitest";
import {
  deleteUploadedFile,
  deleteSessionArtifacts,
  listUploadedFiles,
  uploadFile,
} from "./upload";
import type { UploadedFileRecord } from "./upload";

vi.mock("axios");

const BASE = "http://127.0.0.1:8004";

beforeEach(() => {
  vi.clearAllMocks();
});

// ── Fixtures ──────────────────────────────────────────────────────────────────

const baseFileRecord: UploadedFileRecord = {
  file_upload_id: "upload-1",
  session_id: "session-123",
  original_filename: "hello.txt",
  filename: "hello.txt",
  stored_filename: "upload-1__hello.txt",
  stored_path: "/uploads/hello.txt",
  extension: ".txt",
  mime_type: "text/plain",
  size_bytes: 5,
  uploaded_at: "2026-03-01T10:00:00Z",
  parse_status: "ready",
  searchable: true,
};

// ── uploadFile ────────────────────────────────────────────────────────────────

describe("uploadFile", () => {
  it("sends the file as multipart/form-data to the upload endpoint", async () => {
    vi.mocked(axios.post).mockResolvedValue({
      data: { status: "success", ...baseFileRecord },
    });

    const file = new File(["hello"], "hello.txt", { type: "text/plain" });
    const result = await uploadFile(file, "session-123");

    expect(axios.post).toHaveBeenCalledOnce();
    const [url, formData] = vi.mocked(axios.post).mock.calls[0];
    expect(url).toBe(`${BASE}/api/import/upload`);
    expect(formData).toBeInstanceOf(FormData);
    expect((formData as FormData).get("session_id")).toBe("session-123");
    expect((formData as FormData).get("file")).toBeInstanceOf(File);
    expect(result.status).toBe("success");
  });

  it("returns the full upload record from the response", async () => {
    vi.mocked(axios.post).mockResolvedValue({
      data: { status: "success", ...baseFileRecord },
    });

    const file = new File(["hello"], "hello.txt", { type: "text/plain" });
    const result = await uploadFile(file, "session-123");

    expect(result.file_upload_id).toBe("upload-1");
    expect(result.original_filename).toBe("hello.txt");
    expect(result.parse_status).toBe("ready");
  });

  it("throws when the API call fails", async () => {
    vi.mocked(axios.post).mockRejectedValue(new Error("Upload failed"));

    const file = new File(["hello"], "hello.txt", { type: "text/plain" });
    await expect(uploadFile(file, "session-123")).rejects.toThrow(
      "Upload failed",
    );
  });
});

// ── listUploadedFiles ─────────────────────────────────────────────────────────

describe("listUploadedFiles", () => {
  it("fetches files with session_id as a query param", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: {
        status: "success",
        session_id: "session-123",
        files: [baseFileRecord],
      },
    });

    const files = await listUploadedFiles("session-123");

    expect(axios.get).toHaveBeenCalledWith(`${BASE}/api/import/files`, {
      params: { session_id: "session-123" },
    });
    expect(files).toHaveLength(1);
    expect(files[0].file_upload_id).toBe("upload-1");
  });

  it("returns an empty array when no files exist for the session", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: { status: "success", session_id: "session-123", files: [] },
    });

    const files = await listUploadedFiles("session-123");

    expect(files).toEqual([]);
  });

  it("unwraps the files array from the response envelope", async () => {
    const twoFiles = [
      baseFileRecord,
      { ...baseFileRecord, file_upload_id: "upload-2" },
    ];
    vi.mocked(axios.get).mockResolvedValue({
      data: { status: "success", session_id: "session-123", files: twoFiles },
    });

    const files = await listUploadedFiles("session-123");

    expect(files).toHaveLength(2);
    expect(files[1].file_upload_id).toBe("upload-2");
  });

  it("throws when the API call fails", async () => {
    vi.mocked(axios.get).mockRejectedValue(new Error("Forbidden"));

    await expect(listUploadedFiles("session-123")).rejects.toThrow("Forbidden");
  });
});

// ── deleteUploadedFile ────────────────────────────────────────────────────────

describe("deleteUploadedFile", () => {
  it("sends DELETE to the correct URL with session_id as a query param", async () => {
    vi.mocked(axios.delete).mockResolvedValue({ status: 204 });

    await deleteUploadedFile("session-123", "upload-1");

    expect(axios.delete).toHaveBeenCalledWith(
      `${BASE}/api/import/files/upload-1`,
      { params: { session_id: "session-123" } },
    );
  });

  it("resolves without a return value on success", async () => {
    vi.mocked(axios.delete).mockResolvedValue({ status: 204 });

    const result = await deleteUploadedFile("session-123", "upload-1");

    expect(result).toBeUndefined();
  });

  it("throws when the API call fails", async () => {
    vi.mocked(axios.delete).mockRejectedValue(new Error("Not found"));

    await expect(deleteUploadedFile("session-123", "upload-1")).rejects.toThrow(
      "Not found",
    );
  });
});

// ── deleteSessionArtifacts ────────────────────────────────────────────────────

describe("deleteSessionArtifacts", () => {
  it("sends DELETE to the session endpoint", async () => {
    vi.mocked(axios.delete).mockResolvedValue({ status: 204 });

    await deleteSessionArtifacts("session-123");

    expect(axios.delete).toHaveBeenCalledWith(
      `${BASE}/api/sessions/session-123`,
    );
  });

  it("resolves without a return value on success", async () => {
    vi.mocked(axios.delete).mockResolvedValue({ status: 204 });

    const result = await deleteSessionArtifacts("session-123");

    expect(result).toBeUndefined();
  });

  it("silently succeeds when the backend returns an error (best-effort cleanup)", async () => {
    vi.mocked(axios.delete).mockRejectedValue(new Error("Backend unreachable"));

    // Should not throw — errors are swallowed so the frontend deletion can proceed.
    await expect(
      deleteSessionArtifacts("session-123"),
    ).resolves.toBeUndefined();
  });

  it("silently succeeds when the session never had any backend artifacts (404)", async () => {
    vi.mocked(axios.delete).mockRejectedValue({ response: { status: 404 } });

    await expect(
      deleteSessionArtifacts("session-123"),
    ).resolves.toBeUndefined();
  });
});
