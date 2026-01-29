import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import FileUpload from "./FileUpload";
import userEvent from "@testing-library/user-event";

describe("FileUpload", () => {
  it("renders a file input", () => {
    render(<FileUpload />);

    const fileInput = screen.getByLabelText(/upload file/i);
    expect(fileInput).toBeInTheDocument();
    expect(fileInput).toHaveAttribute("type", "file");
  });

  it("accepts only JSON, CSV, PDF, and TXT files", () => {
    render(<FileUpload />);

    const fileInput = screen.getByLabelText(/upload file/i);
    expect(fileInput).toHaveAttribute("accept", ".json, .csv, .pdf, .txt");
  });

  it("calls onFileSelect when a file is selected", async () => {
    const user = userEvent.setup();
    const handleFileSelect = vi.fn();
    render(<FileUpload onFileSelect={handleFileSelect} />);

    const fileInput = screen.getByLabelText(/upload file/i);
    const testFile = new File(["file content"], "file.json", {
      type: "application/json",
    });

    await user.upload(fileInput, testFile);

    expect(handleFileSelect).toHaveBeenCalledTimes(1);
    expect(handleFileSelect).toHaveBeenCalledWith(testFile);
  });

  it("displays selected file names and sizes", async () => {
    const user = userEvent.setup();
    render(<FileUpload />);

    const fileInput = screen.getByLabelText(/upload file/i);
    const testFile = new File(["file content"], "file.json", {
      type: "application/json",
    });

    await user.upload(fileInput, testFile);

    expect(screen.getByText("file.json")).toBeInTheDocument();
    expect(screen.getByText("12 bytes")).toBeInTheDocument();
  });

  it("removes files when remove button is clicked", async () => {
    const user = userEvent.setup();
    render(<FileUpload />);

    const fileInput = screen.getByLabelText(/upload file/i);
    const testFile = new File(["file content"], "file.json", {
      type: "application/json",
    });

    await user.upload(fileInput, testFile);
    expect(screen.getByText("file.json")).toBeInTheDocument();

    const removeButton = screen.getByRole("button", { name: /remove/i });
    await user.click(removeButton);

    expect(screen.queryByText("file.json")).not.toBeInTheDocument();
  });

  it("supports selecting multiple files", async () => {
    const user = userEvent.setup();
    render(<FileUpload />);

    const fileInput = screen.getByLabelText(/upload file/i);
    const testFile1 = new File(["file content 1"], "file1.json", {
      type: "application/json",
    });
    const testFile2 = new File(["file content 2"], "file2.csv", {
      type: "text/csv",
    });

    await user.upload(fileInput, [testFile1, testFile2]);

    expect(screen.getByText("file1.json")).toBeInTheDocument();
    expect(screen.getByText("file2.csv")).toBeInTheDocument();
  });

  it("adds files when dropped onto the drop zone", async () => {
    render(<FileUpload />);
    const dropzone = screen.getByTestId("file-dropzone");

    const testFile = new File(["file content"], "file.json", {
      type: "application/json",
    });

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [testFile],
      },
    });

    expect(screen.getByText("file.json")).toBeInTheDocument();
  });

  it("calles onFileSelect when files are dropped onto the drop zone", async () => {
    const handleFileSelect = vi.fn();
    render(<FileUpload onFileSelect={handleFileSelect} />);

    const dropzone = screen.getByTestId("file-dropzone");
    const testFile = new File(["file content"], "file.json", {
      type: "application/json",
    });

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [testFile],
      },
    });

    expect(handleFileSelect).toHaveBeenCalledTimes(1);
    expect(handleFileSelect).toHaveBeenCalledWith(testFile);
  });

  it("renders Canel and Submit buttons", () => {
    render(<FileUpload />);

    const cancelButton = screen.getByRole("button", { name: /cancel/i });
    const uploadButton = screen.getByRole("button", { name: /submit/i });

    expect(cancelButton).toBeInTheDocument();
    expect(uploadButton).toBeInTheDocument();
  });

  it("clears all files when Canel button is clicked", async () => {
    const user = userEvent.setup();
    render(<FileUpload />);

    const fileInput = screen.getByLabelText(/upload file/i);
    const testFile1 = new File(["file content 1"], "file1.json", {
      type: "application/json",
    });
    const testFile2 = new File(["file content 2"], "file2.csv", {
      type: "text/csv",
    });

    await user.upload(fileInput, [testFile1, testFile2]);

    expect(screen.getByText("file1.json")).toBeInTheDocument();
    expect(screen.getByText("file2.csv")).toBeInTheDocument();

    const cancelButton = screen.getByRole("button", { name: /cancel/i });
    await user.click(cancelButton);

    expect(screen.queryByText("file1.json")).not.toBeInTheDocument();
    expect(screen.queryByText("file2.csv")).not.toBeInTheDocument();
  });

  it("calles onSumbit with selected files when Submit button is clicked", async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();
    render(<FileUpload onSubmit={handleSubmit} />);

    const fileInput = screen.getByLabelText(/upload file/i);
    const testFile1 = new File(["file content 1"], "file1.json", {
      type: "application/json",
    });
    const testFile2 = new File(["file content 2"], "file2.csv", {
      type: "text/csv",
    });

    await user.upload(fileInput, [testFile1, testFile2]);

    const submitButton = screen.getByRole("button", { name: /submit/i });
    await user.click(submitButton);

    expect(handleSubmit).toHaveBeenCalledTimes(1);
    expect(handleSubmit).toHaveBeenCalledWith([testFile1, testFile2]);
  });

  it("highlights drop zone when dragging over", () => {
    render(<FileUpload />);

    const dropZone = screen.getByTestId("file-dropzone");

    // Initially, no highlight
    expect(dropZone).not.toHaveClass("border-blue-500");

    // Drag enter
    fireEvent.dragEnter(dropZone, {
      dataTransfer: { files: [] },
    });

    // Should now be highlighted
    expect(dropZone).toHaveClass("border-blue-500");

    // Drag leave
    fireEvent.dragLeave(dropZone);

    // Highlight should be gone
    expect(dropZone).not.toHaveClass("border-blue-500");
  });

  it("enables Submit button when files are selected", async () => {
    const user = userEvent.setup();
    render(<FileUpload />);

    const submitButton = screen.getByRole("button", { name: /submit/i });
    const fileInput = screen.getByLabelText(/upload file/i);

    // Initially disabled
    expect(submitButton).toBeDisabled();

    // Add a file
    const testFile = new File(["content"], "test.json", {
      type: "application/json",
    });
    await user.upload(fileInput, testFile);

    // Should now be enabled
    expect(submitButton).toBeEnabled();
  });
});
