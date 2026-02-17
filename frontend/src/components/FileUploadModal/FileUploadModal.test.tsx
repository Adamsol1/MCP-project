import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FileUploadModal } from "./FileUploadModal";

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
