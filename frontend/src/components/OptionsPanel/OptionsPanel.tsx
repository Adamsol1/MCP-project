import { useState } from "react";
import PerspectiveSelector from "../PerspectiveSelector/PerspectiveSelector";
import type { UploadedFileRecord } from "../../services/upload";

/** Props for the OptionsPanel component. */
interface OptionsPanelProps {
  /** The currently active geopolitical perspectives for the active conversation. */
  selectedPerspectives: string[];
  /** Called with the updated perspectives array when the user toggles one. */
  onPerspectiveChange: (perspectives: string[]) => void;
  /** Called when the user clicks the Upload Files button to open the modal. */
  onOpenFileUpload: () => void;
  /** Files that have been successfully uploaded via the FileUploadModal. */
  uploadedFiles?: UploadedFileRecord[];
  /** Called when the user removes a file from the uploaded files list. */
  onFileRemove?: (file: UploadedFileRecord) => void;
}

/** Maximum number of files shown before the "Show X more" toggle appears. */
const VISIBLE_FILE_COUNT = 2;

export function OptionsPanel({
  selectedPerspectives,
  onPerspectiveChange,
  onOpenFileUpload,
  uploadedFiles = [],
  onFileRemove,
}: OptionsPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [showAllFiles, setShowAllFiles] = useState(false);

  const visibleFiles = showAllFiles
    ? uploadedFiles
    : uploadedFiles.slice(0, VISIBLE_FILE_COUNT);

  const hiddenCount = uploadedFiles.length - VISIBLE_FILE_COUNT;

  return (
    <aside
      className={`${
        isCollapsed ? "w-14" : "w-64"
      } bg-surface-muted border-l border-border-muted flex flex-col overflow-hidden`}
    >
      <button
        aria-label="Toggle options"
        onClick={() => setIsCollapsed((prev) => !prev)}
        className="p-2 flex items-center justify-center shrink-0 hover:bg-surface-elevated rounded"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          {isCollapsed ? <path d="M15 18l-6-6 6-6" /> : <path d="M9 18l6-6-6-6" />}
        </svg>
      </button>

      {!isCollapsed && (
        <div className="flex flex-col gap-6 p-4 overflow-y-auto">
          <div>
            <PerspectiveSelector
              selected={selectedPerspectives}
              onChange={onPerspectiveChange}
            />
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-3">
              Files
            </p>

            <button
              onClick={onOpenFileUpload}
              className="w-full p-2 bg-primary-dark text-text-inverse rounded text-sm font-medium hover:bg-primary-hover transition-colors"
            >
              Upload Files
            </button>

            {uploadedFiles.length > 0 && (
              <>
                <ul className="mt-3 flex flex-col gap-1">
                  {visibleFiles.map((file) => (
                    <li
                      key={file.file_upload_id}
                      className="flex items-center justify-between gap-1 text-sm"
                    >
                      <span
                        className="flex-1 truncate text-text-primary"
                        title={file.filename}
                      >
                        {file.filename}
                      </span>
                      <button
                        onClick={() => onFileRemove?.(file)}
                        className="shrink-0 text-text-muted hover:text-error transition-colors"
                        aria-label={`Remove ${file.filename}`}
                      >
                        x
                      </button>
                    </li>
                  ))}
                </ul>

                {uploadedFiles.length > VISIBLE_FILE_COUNT && (
                  <button
                    onClick={() => setShowAllFiles((prev) => !prev)}
                    className="mt-2 text-xs text-primary-dark hover:underline"
                  >
                    {showAllFiles
                      ? "Show less"
                      : `Show ${hiddenCount} more`}
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </aside>
  );
}
