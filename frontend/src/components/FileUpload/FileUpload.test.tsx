import { render, screen } from "@testing-library/react";
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

  it("calles onFileSelect when a file is selected", async () => {
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
});
