import FileUpload from "../FileUpload/FileUpload";

interface FileUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onFileSelect: (file: File) => void;
  onSubmit: (files: File[]) => void;
}

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
        className="bg-white rounded-lg p-6 w-full max-w-lg"
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Upload Files</h2>
          <button
            aria-label="close"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            X
          </button>
        </div>
        <FileUpload onFileSelect={onFileSelect} onSubmit={onSubmit} />
      </div>
    </div>
  );
}
