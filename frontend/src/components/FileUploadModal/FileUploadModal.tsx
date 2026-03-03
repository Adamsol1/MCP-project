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
}: FileUploadModalProps) {
  if (!isOpen) return null;

  return (
    <div
      data-testid="modal-backdrop"
      onClick={onClose}
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
    >
      <div
        data-testid="modal-content"
        onClick={(e) => e.stopPropagation()}
        className="bg-surface rounded-lg p-6 w-full max-w-lg"
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Upload Files</h2>
          <button
            aria-label="close"
            onClick={onClose}
            className="text-text-muted hover:text-text-secondary"
          >
            X
          </button>
        </div>
        <FileUpload onFileSelect={onFileSelect} onSubmit={onSubmit} />
      </div>
    </div>
  );
}
