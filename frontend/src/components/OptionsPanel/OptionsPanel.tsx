import { useState } from "react";
import PerspectiveSelector from "../PerspectiveSelector/PerspectiveSelector";

/** Props for the OptionsPanel component. */
interface OptionsPanelProps {
  /** The currently active geopolitical perspectives for the active conversation. */
  selectedPerspectives: string[];
  /** Called with the updated perspectives array when the user toggles one. */
  onPerspectiveChange: (perspectives: string[]) => void;
  /** Called when the user clicks the Upload Files button to open the modal. */
  onOpenFileUpload: () => void;
  /** Files that have been successfully uploaded via the FileUploadModal. */
  uploadedFiles?: File[];
  /** Called when the user removes a file from the uploaded files list. */
  onFileRemove?: (file: File) => void;
}

/**
 * Right-hand sidebar that exposes analysis configuration for the active conversation.
 *
 * Collapsible: clicking the toggle button shrinks the panel to a slim w-14 icon
 * rail so the user can reclaim horizontal space without losing the toggle itself.
 * Width snaps instantly (no CSS transition) to avoid content squishing — matching
 * the same decision made for the left Sidebar.
 *
 * Contents (visible when expanded):
 *   - "Perspectives" section — PerspectiveSelector for geopolitical analysis angles.
 *   - "Files" section — Upload Files button (opens modal) + a collapsible list of
 *     files already uploaded during this session. If more than 2 files are present,
 *     only the first 2 are shown and a "Show X more" toggle reveals the rest.
 *
 * Local state:
 *   isCollapsed  — whether the panel is in its narrow rail mode.
 *   showAllFiles — whether the full file list is expanded past the 2-file threshold.
 */

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
  /** Controls whether the full uploaded-files list is expanded. */
  const [showAllFiles, setShowAllFiles] = useState(false);

  /** Slice of files shown based on showAllFiles toggle. */
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
      {/* Toggle button — chevron points left (‹) when expanded to signal "collapse",
          right (›) when collapsed to signal "expand".
          Mirrors the chevron logic used in the left Sidebar. */}
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
          {isCollapsed
            ? <path d="M15 18l-6-6 6-6" />  /* ‹ chevron-left  = expand  */
            : <path d="M9 18l6-6-6-6" />    /* › chevron-right = collapse */
          }
        </svg>
      </button>

      {/* Panel content — hidden entirely when collapsed. */}
      {!isCollapsed && (
        <div className="flex flex-col gap-6 p-4 overflow-y-auto">

          {/* ── Section: Perspectives ─────────────────────────────── */}
          <div>
            <PerspectiveSelector
              selected={selectedPerspectives}
              onChange={onPerspectiveChange}
            />
          </div>

          {/* ── Section: Files ────────────────────────────────────── */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-3">
              Files
            </p>

            {/* Opens the FileUploadModal overlay */}
            <button
              onClick={onOpenFileUpload}
              className="w-full p-2 bg-primary-dark text-text-inverse rounded text-sm font-medium hover:bg-primary-hover transition-colors"
            >
              Upload Files
            </button>

            {/* Uploaded file list — only shown when at least one file exists */}
            {uploadedFiles.length > 0 && (
              <>
                <ul className="mt-3 flex flex-col gap-1">
                  {visibleFiles.map((file) => (
                    <li
                      key={`${file.name}-${file.size}`}
                      className="flex items-center justify-between gap-1 text-sm"
                    >
                      <span
                        className="flex-1 truncate text-text-primary"
                        title={file.name}
                      >
                        {file.name}
                      </span>
                      <button
                        onClick={() => onFileRemove?.(file)}
                        className="shrink-0 text-text-muted hover:text-error transition-colors"
                        aria-label={`Remove ${file.name}`}
                      >
                        ✕
                      </button>
                    </li>
                  ))}
                </ul>

                {/* Show more / show less toggle — only when list exceeds threshold */}
                {uploadedFiles.length > VISIBLE_FILE_COUNT && (
                  <button
                    onClick={() => setShowAllFiles((prev) => !prev)}
                    className="mt-2 text-xs text-primary-dark hover:underline"
                  >
                    {showAllFiles
                      ? "Show less ▴"
                      : `Show ${hiddenCount} more ▾`}
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
