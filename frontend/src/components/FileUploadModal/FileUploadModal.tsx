import FileUpload from "../FileUpload/FileUpload";

/** Props for the FileUploadModal component. */
interface FileUploadModalProps {
  /** Whether the modal is currently visible. When false the component renders nothing. */
  isOpen: boolean;
  /** Called when the user dismisses the modal (backdrop click or × button). */
  onClose: () => void;
  /** Called each time the user selects an individual file inside the dropzone. Optional. */
  onFileSelect?: (file: File) => void;
  /** Called when the user clicks Submit with the full list of queued files. */
  onSubmit: (files: File[]) => void;
  /** True while files are being uploaded to the server. */
  isUploading?: boolean;
  /** How many files have been uploaded out of the total batch. */
  uploadProgress?: { current: number; total: number };
}

/**
 * Modal overlay wrapping the FileUpload component.
 *
 * Renders nothing when isOpen is false — the component has no DOM presence
 * while closed, avoiding hidden layout impact.
 *
 * Click behaviour:
 *   - Clicking the semi-transparent backdrop calls onClose.
 *   - Clicking inside the white content panel stops event propagation so the
 *     backdrop handler is not triggered and the modal stays open.
 */
export function FileUploadModal({
  isOpen,
  onClose,
  onFileSelect,
  onSubmit,
  isUploading = false,
  uploadProgress = { current: 0, total: 0 },
}: FileUploadModalProps) {
  if (!isOpen) return null;

  const progressPercent =
    uploadProgress.total > 0
      ? Math.round((uploadProgress.current / uploadProgress.total) * 100)
      : 0;

  return (
    <div
      data-testid="modal-backdrop"
      onClick={isUploading ? undefined : onClose}
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
    >
      <div
        data-testid="modal-content"
        onClick={(e) => e.stopPropagation()}
        className="bg-surface rounded-lg p-6 w-full max-w-lg relative"
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Upload Files</h2>
          <button
            aria-label="close"
            onClick={onClose}
            disabled={isUploading}
            className="text-text-muted hover:text-text-secondary disabled:opacity-40 disabled:cursor-not-allowed"
          >
            X
          </button>
        </div>

        {isUploading ? (
          <div className="py-8 flex flex-col items-center gap-4">
            {/* Throbber */}
            <div className="w-10 h-10 rounded-full border-4 border-border border-t-primary animate-spin" />
            <p className="text-sm font-medium text-text-primary">
              Uploading {uploadProgress.current} of {uploadProgress.total}{" "}
              {uploadProgress.total === 1 ? "file" : "files"}…
            </p>
            {/* Progress bar */}
            <div className="w-full h-2 rounded-full bg-surface-elevated overflow-hidden">
              <div
                className="h-full rounded-full bg-primary transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        ) : (
          <FileUpload onFileSelect={onFileSelect} onSubmit={onSubmit} />
        )}
      </div>
    </div>
  );
}
