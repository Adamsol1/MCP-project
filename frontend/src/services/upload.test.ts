import axios from "axios";
import { describe, expect, it, vi } from "vitest";

import {
  deleteUploadedFile,
  listUploadedFiles,
  uploadFile,
} from "./upload";

vi.mock("axios");

describe("upload service", () => {
  it("uploads file with session_id in multipart body", async () => {
    const fakeResponse = {
      data: {
        status: "success",
        file_upload_id: "upload-1",
      },
    };
    vi.mocked(axios.post).mockResolvedValue(fakeResponse as never);

    const file = new File(["hello"], "hello.txt", { type: "text/plain" });
    const result = await uploadFile(file, "session-123");

    expect(axios.post).toHaveBeenCalledOnce();
    const [url, formData] = vi.mocked(axios.post).mock.calls[0];
    expect(url).toBe("http://localhost:8000/api/import/upload");
    expect(formData).toBeInstanceOf(FormData);
    expect((formData as FormData).get("session_id")).toBe("session-123");
    expect((formData as FormData).get("file")).toBeInstanceOf(File);
    expect(result.status).toBe("success");
  });

  it("lists uploaded files by session", async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: {
        status: "success",
        session_id: "session-123",
        files: [{ file_upload_id: "upload-1", filename: "hello.txt" }],
      },
    } as never);

    const files = await listUploadedFiles("session-123");

    expect(axios.get).toHaveBeenCalledWith(
      "http://localhost:8000/api/import/files",
      { params: { session_id: "session-123" } },
    );
    expect(files).toHaveLength(1);
    expect(files[0].file_upload_id).toBe("upload-1");
  });

  it("deletes uploaded file by id and session", async () => {
    vi.mocked(axios.delete).mockResolvedValue({ status: 204 } as never);

    await deleteUploadedFile("session-123", "upload-1");

    expect(axios.delete).toHaveBeenCalledWith(
      "http://localhost:8000/api/import/files/upload-1",
      { params: { session_id: "session-123" } },
    );
  });
});
