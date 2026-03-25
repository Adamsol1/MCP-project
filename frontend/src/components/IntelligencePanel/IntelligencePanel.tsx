import { useState } from "react";
import { useWorkspace } from "../../contexts/WorkspaceContext/WorkspaceContext";
import PirSourcesView from "../PirSourcesView/PirSourcesView";
import CollectionStatsView from "../CollectionStatsView/CollectionStatsView";
import CollectionStatsModal from "../CollectionStatsModal/CollectionStatsModal";
import PerspectiveSelector from "../PerspectiveSelector/PerspectiveSelector";
import type { UploadedFileRecord } from "../../services/upload";
import type { CollectionStatus } from "../../services/dialogue";

const VISIBLE_FILE_COUNT = 3;

interface IntelligencePanelProps {
  selectedPerspectives?: string[];
  onPerspectiveChange?: (perspectives: string[]) => void;
  onOpenFileUpload?: () => void;
  uploadedFiles?: UploadedFileRecord[];
  onFileRemove?: (file: UploadedFileRecord) => void;
  isCollecting?: boolean;
  collectionStatus?: CollectionStatus | null;
}

export default function IntelligencePanel({
  selectedPerspectives = ["NEUTRAL"],
  onPerspectiveChange = () => {},
  onOpenFileUpload = () => {},
  uploadedFiles = [],
  onFileRemove,
  isCollecting = false,
  collectionStatus = null,
}: IntelligencePanelProps) {
  const { activePhase, collectionData } = useWorkspace();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [showAllFiles, setShowAllFiles] = useState(false);

  const visibleFiles = showAllFiles
    ? uploadedFiles
    : uploadedFiles.slice(0, VISIBLE_FILE_COUNT);
  const hiddenCount = uploadedFiles.length - VISIBLE_FILE_COUNT;

  const phaseLabel = activePhase.toUpperCase();

  function renderPhaseContent() {
    switch (activePhase) {
      case "direction":
        return (
          <>
            {isCollecting && collectionStatus ? (
              <section className="rounded-lg border border-border-muted bg-surface-muted/70 p-2 shadow-sm">
                <CollectionStatusDisplay status={collectionStatus} />
              </section>
            ) : (
              <section className="rounded-lg border border-border-muted bg-surface-muted/70 p-2 shadow-sm">
                <PerspectiveSelector
                  selected={selectedPerspectives}
                  onChange={onPerspectiveChange}
                />
              </section>
            )}
            <section className="rounded-lg border border-border-muted bg-surface-muted/70 p-2 shadow-sm">
              <PirSourcesView />
            </section>
          </>
        );

      case "collection":
        return (
          <>
            <section className="rounded-lg border border-border-muted bg-surface-muted/70 p-2 shadow-sm">
              <FileUploadSection
                uploadedFiles={uploadedFiles}
                visibleFiles={visibleFiles}
                hiddenCount={hiddenCount}
                showAllFiles={showAllFiles}
                onToggleShowAll={() => setShowAllFiles((prev) => !prev)}
                onOpenFileUpload={onOpenFileUpload}
                onFileRemove={onFileRemove}
              />
            </section>
            <section className="rounded-lg border border-border-muted bg-surface-muted/70 p-2 shadow-sm">
              <CollectionStatsView
                collectionData={collectionData}
                onOpenModal={() => setIsModalOpen(true)}
              />
            </section>
          </>
        );

      case "processing":
        return (
          <>
            <section className="rounded-lg border border-border-muted bg-surface-muted/70 p-2 shadow-sm">
              <FileUploadSection
                uploadedFiles={uploadedFiles}
                visibleFiles={visibleFiles}
                hiddenCount={hiddenCount}
                showAllFiles={showAllFiles}
                onToggleShowAll={() => setShowAllFiles((prev) => !prev)}
                onOpenFileUpload={onOpenFileUpload}
                onFileRemove={onFileRemove}
              />
            </section>
            <section className="rounded-lg border border-border-muted bg-surface-muted/70 p-2 shadow-sm">
              <p className="text-xs text-text-secondary">
                Processing artifacts will appear here.
              </p>
            </section>
          </>
        );

      case "analysis":
        return (
          <>
            <section className="rounded-lg border border-border-muted bg-surface-muted/70 p-2 shadow-sm">
              <FileUploadSection
                uploadedFiles={uploadedFiles}
                visibleFiles={visibleFiles}
                hiddenCount={hiddenCount}
                showAllFiles={showAllFiles}
                onToggleShowAll={() => setShowAllFiles((prev) => !prev)}
                onOpenFileUpload={onOpenFileUpload}
                onFileRemove={onFileRemove}
              />
            </section>
            <section className="rounded-lg border border-border-muted bg-surface-muted/70 p-2 shadow-sm">
              <p className="text-xs text-text-secondary">
                Analysis outputs will appear here.
              </p>
            </section>
          </>
        );

      default:
        return null;
    }
  }

  return (
    <div className="h-full flex flex-col bg-surface">
      <header className="border-b border-border-muted px-3 py-2">
        <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-text-muted">
          Intelligence Workspace
        </p>
        <h2 className="mt-1 text-xs font-semibold text-text-primary">{phaseLabel}</h2>
      </header>

      <div className="flex-1 overflow-y-auto px-2 py-2 scrollbar-chatgpt">
        <div className="flex flex-col gap-2">
          {renderPhaseContent()}
        </div>
      </div>

      <CollectionStatsModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        collectionData={collectionData}
      />
    </div>
  );
}

function CollectionStatusDisplay({ status }: { status: CollectionStatus }) {
  const entries = Object.entries(status.sources);

  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary mb-2">
        Collecting
      </p>
      <ul className="flex flex-col gap-1.5">
        {entries.map(([source, info]) => {
          const isActive = status.current_source === source;
          const isDone = info.call_count > 0 && !isActive;
          const showActivity = isActive && status.current_activity;
          return (
            <li key={source} className="flex flex-col gap-0.5">
              <div className="flex items-center gap-2 text-xs">
                <span className={`shrink-0 w-3.5 text-center ${
                  isDone ? "text-success" : isActive ? "text-primary" : "text-text-muted"
                }`}>
                  {isDone ? "✓" : isActive ? "→" : "○"}
                </span>
                <span className={
                  isDone ? "text-text-secondary" :
                  isActive ? "text-text-primary font-medium" :
                  "text-text-muted"
                }>
                  {source}
                </span>
                {info.call_count > 0 && (
                  <span className="ml-auto text-[10px] text-text-muted tabular-nums">
                    {info.call_count}
                  </span>
                )}
                {isActive && !showActivity && (
                  <span className="ml-auto flex gap-0.5">
                    <span className="w-1 h-1 rounded-full bg-primary animate-bounce [animation-delay:0ms]" />
                    <span className="w-1 h-1 rounded-full bg-primary animate-bounce [animation-delay:150ms]" />
                    <span className="w-1 h-1 rounded-full bg-primary animate-bounce [animation-delay:300ms]" />
                  </span>
                )}
              </div>
              {showActivity && (
                <div className="flex items-center gap-1.5 pl-5 text-[10px] text-text-muted">
                  <span>{status.current_activity}</span>
                  <span className="flex gap-0.5">
                    <span className="w-1 h-1 rounded-full bg-text-muted animate-bounce [animation-delay:0ms]" />
                    <span className="w-1 h-1 rounded-full bg-text-muted animate-bounce [animation-delay:150ms]" />
                    <span className="w-1 h-1 rounded-full bg-text-muted animate-bounce [animation-delay:300ms]" />
                  </span>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

interface FileUploadSectionProps {
  uploadedFiles: UploadedFileRecord[];
  visibleFiles: UploadedFileRecord[];
  hiddenCount: number;
  showAllFiles: boolean;
  onToggleShowAll: () => void;
  onOpenFileUpload: () => void;
  onFileRemove?: (file: UploadedFileRecord) => void;
}

function FileUploadSection({
  uploadedFiles,
  visibleFiles,
  hiddenCount,
  showAllFiles,
  onToggleShowAll,
  onOpenFileUpload,
  onFileRemove,
}: FileUploadSectionProps) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary mb-2">
        Files
      </p>

      <button
        onClick={onOpenFileUpload}
        className="w-full py-1 px-2 bg-primary-dark text-text-inverse rounded text-xs font-medium hover:bg-primary-hover transition-colors"
      >
        Upload Files
      </button>

      {uploadedFiles.length > 0 && (
        <>
          <ul className="mt-2 flex flex-col gap-0.5">
            {visibleFiles.map((file) => (
              <li
                key={file.file_upload_id}
                className="flex items-center justify-between gap-1 text-xs"
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
                  ✕
                </button>
              </li>
            ))}
          </ul>

          {uploadedFiles.length > 3 && (
            <button
              onClick={onToggleShowAll}
              className="mt-2 text-xs text-primary-dark hover:underline"
            >
              {showAllFiles ? "Show less" : `Show ${hiddenCount} more`}
            </button>
          )}
        </>
      )}
    </div>
  );
}
