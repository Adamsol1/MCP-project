import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FileUploadModal } from "./FileUploadModal";
import { axe } from "vitest-axe";

describe("FileUploadModal", () => {
  // ---------- Visibility ----------

  it("renders nothing when isOpen is false", () => {
    const { container } = render(
      <FileUploadModal
        isOpen={false}
        onClose={vi.fn()}
        onFileSelect={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    expect(container.innerHTML).toBe("");
  });

  it("renders a backdrop and modal content when isOpen is true", () => {
    render(
      <FileUploadModal
        isOpen={true}
        onClose={vi.fn()}
        onFileSelect={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    // Backdrop exists
    expect(screen.getByTestId("modal-backdrop")).toBeInTheDocument();
    // Modal content area exists
    expect(screen.getByTestId("modal-content")).toBeInTheDocument();
  });

  it("renders a title in the modal", () => {
    render(
      <FileUploadModal
        isOpen={true}
        onClose={vi.fn()}
        onFileSelect={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByText(/upload files/i)).toBeInTheDocument();
  });

  // ---------- Close behavior ----------

  it("calls onClose when the backdrop is clicked", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <FileUploadModal
        isOpen={true}
        onClose={onClose}
        onFileSelect={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    await user.click(screen.getByTestId("modal-backdrop"));

    expect(onClose).toHaveBeenCalledOnce();
  });

  it("does not call onClose when clicking inside the modal content", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <FileUploadModal
        isOpen={true}
        onClose={onClose}
        onFileSelect={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    await user.click(screen.getByTestId("modal-content"));

    expect(onClose).not.toHaveBeenCalled();
  });

  it("renders a close button that calls onClose", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <FileUploadModal
        isOpen={true}
        onClose={onClose}
        onFileSelect={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: /close/i }));

    expect(onClose).toHaveBeenCalledOnce();
  });

  // ---------- FileUpload integration ----------

  it("renders the FileUpload component inside the modal", () => {
    render(
      <FileUploadModal
        isOpen={true}
        onClose={vi.fn()}
        onFileSelect={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    // FileUpload renders a dropzone
    expect(screen.getByTestId("file-dropzone")).toBeInTheDocument();
  });
});

describe("FileUploadModal — uploading state", () => {
  it("shows upload progress text when isUploading is true", () => {
    render(
      <FileUploadModal
        isOpen={true}
        onClose={vi.fn()}
        onFileSelect={vi.fn()}
        onSubmit={vi.fn()}
        isUploading={true}
        uploadProgress={{ current: 1, total: 3 }}
      />,
    );

    expect(screen.getByText(/uploading 1 of 3 files/i)).toBeInTheDocument();
  });

  it("shows 'file' (singular) when total is 1", () => {
    render(
      <FileUploadModal
        isOpen={true}
        onClose={vi.fn()}
        onFileSelect={vi.fn()}
        onSubmit={vi.fn()}
        isUploading={true}
        uploadProgress={{ current: 1, total: 1 }}
      />,
    );

    expect(screen.getByText(/uploading 1 of 1 file…/i)).toBeInTheDocument();
  });

  it("does not call onClose when backdrop is clicked while uploading", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <FileUploadModal
        isOpen={true}
        onClose={onClose}
        onFileSelect={vi.fn()}
        onSubmit={vi.fn()}
        isUploading={true}
        uploadProgress={{ current: 2, total: 5 }}
      />,
    );

    // Backdrop click is disabled during upload (onClick set to undefined)
    await user.click(screen.getByTestId("modal-backdrop"));

    expect(onClose).not.toHaveBeenCalled();
  });

  it("shows progress percentage when total > 0", () => {
    render(
      <FileUploadModal
        isOpen={true}
        onClose={vi.fn()}
        onFileSelect={vi.fn()}
        onSubmit={vi.fn()}
        isUploading={true}
        uploadProgress={{ current: 2, total: 4 }}
      />,
    );

    // progressPercent = 50%, applied as inline style — check the bar exists
    const progressBar = document.querySelector("[style]");
    expect(progressBar).toBeInTheDocument();
  });
});

describe("FileUploadModal — accessibility (WCAG 2.1 AA)", () => {
  it("has no violations when open", async () => {
    const { container } = render(
      <FileUploadModal
        isOpen={true}
        onClose={vi.fn()}
        onFileSelect={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
