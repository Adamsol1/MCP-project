import { useState } from "react";

/** Props for the FileUpload component. */
interface FileUploadProps {
  /** Called for each individual file as it is added to the queue. */
  onFileSelect?: (file: File) => void;
  /** Called when the user clicks Submit with the full list of queued files. */
  onSubmit?: (files: File[]) => void;
}

/**
 * Drag-and-drop file upload component with a queued file list.
 *
 * Manages its own file queue in local state (selectedFiles). Files can be added
 * by clicking the drop zone to open the browser file picker, or by dragging
 * files onto it. Multiple files are supported. Each queued file can be removed
 * individually before submission.
 *
 * State:
 *   selectedFiles  — the current queue of File objects waiting to be submitted.
 *   isDraggingOver — true while a drag is in progress over the drop zone;
 *                    used to apply a blue highlight to the border.
 */
export default function FileUpload({
  onFileSelect,
  onSubmit,
}: FileUploadProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isDraggingOver, setIsDraggingOver] = useState(false);

  /**
   * Handles the native file input change event (browser file picker).
   * Appends newly selected files to the queue and notifies onFileSelect for each.
   * Resets the input value so the same file can be re-selected after removal.
   *
   * @param event - The React change event from the hidden <input type="file">.
   */
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      const newFiles = Array.from(files);
      setSelectedFiles((prev) => [...prev, ...newFiles]);
      newFiles.forEach((file) => {
        if (onFileSelect) {
          onFileSelect(file);
        }
      });
    }
    event.target.value = ""; // Reset so the same file can be re-uploaded after removal.
  };

  /**
   * Prevents the browser's default behaviour of navigating to (or displaying)
   * the dropped file when the user drags over the drop zone.
   *
   * @param event - The React drag-over event.
   */
  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  };

  /**
   * Sets the dragging-over highlight when a drag enters the drop zone.
   *
   * @param event - The React drag-enter event.
   */
  const handleDragEnter = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDraggingOver(true);
  };

  /**
   * Clears the dragging-over highlight when the drag leaves the drop zone.
   *
   * Uses relatedTarget to check whether focus moved to a child element — if so,
   * the drag is still inside the zone and the highlight should not be removed.
   *
   * @param event - The React drag-leave event.
   */
  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (!event.currentTarget.contains(event.relatedTarget as Node)) {
      setIsDraggingOver(false);
    }
  };

  /**
   * Handles a file drop onto the drop zone.
   * Appends the dropped files to the queue and notifies onFileSelect for each.
   *
   * @param event - The React drop event containing the dragged files.
   */
  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDraggingOver(false);
    const files = event.dataTransfer.files;
    if (files && files.length > 0) {
      const newFiles = Array.from(files);
      setSelectedFiles((prev) => [...prev, ...newFiles]);
      newFiles.forEach((file) => {
        if (onFileSelect) {
          onFileSelect(file);
        }
      });
    }
  };

  /** Clears the entire file queue without submitting. */
  const handleCancel = () => {
    setSelectedFiles([]);
  };

  /** Passes the current queue to onSubmit and clears the queue on completion. */
  const handleSubmit = () => {
    if (onSubmit) {
      onSubmit(selectedFiles);
      setSelectedFiles([]);
    }
  };

  /**
   * Converts a raw byte count into a human-readable size string.
   *
   * @param bytes - File size in bytes.
   * @returns A formatted string: e.g. "512 bytes", "3.50 KB", "1.20 MB".
   */
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} bytes`;
    else if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    else return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  /**
   * Removes a single file from the queue by reference equality.
   *
   * @param fileToRemove - The File object to remove.
   */
  const handleRemove = (fileToRemove: File) => {
    setSelectedFiles((prev) => prev.filter((file) => file !== fileToRemove));
  };

  return (
    <div className="w-full  mx-auto p-4">
      {/* Drop Zone — clicking the label opens the hidden file input. */}
      <div
        data-testid="file-dropzone"
        onDragOver={handleDragOver}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed p-42 rounded-lg min-h-64 text-center transition-colors cursor-pointer ${
          isDraggingOver
            ? "border-primary bg-primary-subtle"
            : "border-border hover:border-primary"
        }`}
      >
        <label
          htmlFor="file-upload"
          className="absolute inset-0 flex items-center justify-center cursor-pointer"
        >
          <span className="sr-only">Upload File</span>
          <div className="text-text-secondary">
            <p className="text-2xl font-normal">Drag & drop files here</p>
            <p className="text-md">or click to browse</p>
            <p className="text-sm mt-2 text-text-muted">
              Supported: .json, .csv, .pdf, .txt
            </p>
          </div>
        </label>
        {/* Hidden input — triggered by the label above. */}
        <input
          id="file-upload"
          type="file"
          accept=".json, .csv, .pdf, .txt"
          onChange={handleFileChange}
          multiple={true}
          className="hidden"
        />
      </div>

      {/* File List — only shown when at least one file is queued. */}
      {selectedFiles.length > 0 && (
        <div className="mt-4 space-y-2">
          {selectedFiles.map((file) => (
            <div
              key={file.name}
              className="flex items-center justify-between bg-surface-muted p-3 rounded-lg"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-text-primary truncate">
                  {file.name}
                </p>
                <p className="text-xs text-text-secondary">
                  {formatFileSize(file.size)}
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleRemove(file)}
                className="ml-4 text-error hover:text-error-dark text-sm font-medium"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Action Buttons — Submit is disabled until at least one file is queued. */}
      <div className="mt-6 flex gap-3 justify-end">
        <button
          type="button"
          onClick={handleCancel}
          className="px-4 py-2 text-text-secondary hover:text-text-primary font-medium"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSubmit}
          disabled={selectedFiles.length === 0}
          className={`px-4 py-2 rounded-lg font-medium ${
            selectedFiles.length === 0
              ? "bg-surface-elevated text-text-secondary cursor-not-allowed"
              : "bg-primary text-text-inverse hover:bg-primary-dark"
          }`}
        >
          Submit
        </button>
      </div>
    </div>
  );
}
