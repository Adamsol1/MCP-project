import { useState } from "react";
import type { ReactNode } from "react";
import { useT } from "../../i18n/useT";
import { useWorkspace } from "../../contexts/WorkspaceContext/WorkspaceContext";
import { HelpModal, HelpButton } from "../HelpModal/HelpModal";
import type { DialoguePhase } from "../../types/dialogue";
import type { PhaseReviewItem, ProcessingData } from "../../types/conversation";
import PirSourcesView from "../PirSourcesView/PirSourcesView";
import CollectionStatsView from "../CollectionStatsView/CollectionStatsView";
import CollectionStatsModal from "../CollectionStatsModal/CollectionStatsModal";
import ReviewActivityModal from "../ReviewActivityModal/ReviewActivityModal";
import PerspectiveSelector from "../PerspectiveSelector/PerspectiveSelector";
import type { UploadedFileRecord } from "../../services/upload/upload";
import type { CollectionStatus } from "../../services/dialogue/dialogue";

const VISIBLE_FILE_COUNT = 3;

interface IntelligencePanelProps {
  phase: DialoguePhase;
  selectedPerspectives?: string[];
  onPerspectiveChange?: (perspectives: string[]) => void;
  onOpenFileUpload?: () => void;
  uploadedFiles?: UploadedFileRecord[];
  onFileRemove?: (file: UploadedFileRecord) => void;
  isCollecting?: boolean;
  collectionStatus?: CollectionStatus | null;
}

export default function IntelligencePanel({
  phase,
  selectedPerspectives = ["NEUTRAL"],
  onPerspectiveChange = () => {},
  onOpenFileUpload = () => {},
  uploadedFiles = [],
  onFileRemove,
  isCollecting = false,
  collectionStatus = null,
}: IntelligencePanelProps) {
  const { collectionData, pirData, reviewActivity } = useWorkspace();
  const t = useT();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [reviewFocusAttempt, setReviewFocusAttempt] = useState<number | undefined>(undefined);
  const [showAllFiles, setShowAllFiles] = useState(false);
  const [isReviewHelpOpen, setIsReviewHelpOpen] = useState(false);
  const [isStatsHelpOpen, setIsStatsHelpOpen] = useState(false);

  const visibleFiles = showAllFiles
    ? uploadedFiles
    : uploadedFiles.slice(0, VISIBLE_FILE_COUNT);
  const hiddenCount = uploadedFiles.length - VISIBLE_FILE_COUNT;

  const phaseLabel = t.phaseLabels[phase] ?? phase.toUpperCase();

  function renderPhaseContent() {
    switch (phase) {
      case "direction":
        return (
          <>
            {isCollecting && collectionStatus ? (
              <PanelSection label="Collecting" first>
                <CollectionStatusDisplay status={collectionStatus} />
              </PanelSection>
            ) : (
              <PanelSection label="Perspective" first>
                <PerspectiveSelector
                  selected={selectedPerspectives}
                  onChange={onPerspectiveChange}
                />
              </PanelSection>
            )}
            {pirData && (
              <PanelSection label="PIR Sources">
                <PirSourcesView />
              </PanelSection>
            )}
          </>
        );

      case "collection":
      case "processing":
      case "analysis":
        return (
          <PanelSection label="Files" first>
            <FileUploadSection
              uploadedFiles={uploadedFiles}
              visibleFiles={visibleFiles}
              hiddenCount={hiddenCount}
              showAllFiles={showAllFiles}
              onToggleShowAll={() => setShowAllFiles((prev) => !prev)}
              onOpenFileUpload={onOpenFileUpload}
              onFileRemove={onFileRemove}
            />
          </PanelSection>
        );

      default:
        return null;
    }
  }

  return (
    <div className="h-full flex flex-col bg-surface">
      <header className="h-14 border-b border-border px-3 flex flex-col justify-center">
        <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-text-muted">
          {t.intelligenceWorkspace}
        </p>
        <h2 className="mt-1 text-xs font-semibold text-text-primary">
          {phaseLabel}
        </h2>
      </header>

      <div className="flex-1 overflow-y-auto px-3 py-4 scrollbar-chatgpt">
        <div className="flex flex-col">
          {renderPhaseContent()}
          {reviewActivity.length > 0 && (
            <PanelSection
              label="Review Activity"
              headerRight={<HelpButton onClick={() => setIsReviewHelpOpen(true)} label="Review Activity help" />}
            >
              <ReviewActivitySection
                activity={reviewActivity}
                onOpenReviewModal={(attempt) => {
                  setReviewFocusAttempt(attempt);
                  setReviewModalOpen(true);
                }}
              />
            </PanelSection>
          )}
          {collectionData && (
            <PanelSection
              label="Collection Stats"
              headerRight={<HelpButton onClick={() => setIsStatsHelpOpen(true)} label="Collection Stats help" />}
            >
              <CollectionStatsView
                collectionData={collectionData}
                onOpenModal={() => setIsModalOpen(true)}
              />
            </PanelSection>
          )}
        </div>
      </div>

      <CollectionStatsModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        collectionData={collectionData}
      />
      <ReviewActivityModal
        isOpen={reviewModalOpen}
        onClose={() => setReviewModalOpen(false)}
        activity={reviewActivity}
        focusAttempt={reviewFocusAttempt}
      />
      <HelpModal
        isOpen={isReviewHelpOpen}
        onClose={() => setIsReviewHelpOpen(false)}
        title="Review Activity"
        sections={[
          {
            heading: "What is Review Activity?",
            body: "Between each phase, an AI reviewer evaluates the output before it's shown to you. This acts as an automatic quality gate — checking for completeness, accuracy, and alignment with your intelligence requirements.",
          },
          {
            heading: "Approved vs Rejected",
            body: "If the output meets quality standards it is marked Approved and passed to the next phase. If it falls short, it is Rejected and the AI regenerates the output using the reviewer's feedback. This loop can repeat up to a set number of attempts.",
          },
          {
            heading: "Reading the entries",
            body: "Each entry shows which phase it belongs to, the attempt number, and whether it was approved or rejected. Click an entry to open the full Review Activity modal where you can read the AI feedback and the complete generated transcript for that attempt.",
          },
        ]}
      />
      <HelpModal
        isOpen={isStatsHelpOpen}
        onClose={() => setIsStatsHelpOpen(false)}
        title="Collection Stats"
        sections={[
          {
            heading: "What are Collection Stats?",
            body: "Collection Stats show a summary of all intelligence items gathered during the Collection phase, broken down by source. The total count and number of active sources are shown at a glance.",
          },
          {
            heading: "Available sources",
            body: "AlienVault OTX provides open threat exchange feeds. Web Search queries the live web for relevant articles and reports. Knowledge Bank is your organisation's curated internal intelligence. Uploaded Documents includes any PDFs or files you have uploaded to this session.",
          },
          {
            heading: "Reading the breakdown",
            body: "Each source row shows how many items were collected from it. A source marked Empty returned no usable content. Click 'View Raw Data' to open the full Collection Stats modal with a visual breakdown chart and all collected items.",
          },
        ]}
      />
    </div>
  );
}

function PanelSection({ label, children, first = false, headerRight }: { label: string; children: ReactNode; first?: boolean; headerRight?: ReactNode }) {
  return (
    <>
      {!first && <hr className="border-border" />}
      <section className={first ? "pb-4" : "py-4"}>
        <div className="mb-3 flex items-center justify-between gap-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-muted">
            {label}
          </p>
          {headerRight}
        </div>
        {children}
      </section>
    </>
  );
}

function CollectionStatusDisplay({ status }: { status: CollectionStatus }) {
  const t = useT();
  const entries = Object.entries(status.sources);

  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary mb-2">
        {t.collecting}
      </p>
      <ul className="flex flex-col gap-1.5">
        {entries.map(([source, info]) => {
          const isActive = status.current_source === source;
          const isDone = info.call_count > 0 && !isActive;
          const showActivity = isActive && status.current_activity;
          return (
            <li key={source} className="flex flex-col gap-0.5">
              <div className="flex items-center gap-2 text-xs">
                <span
                  className={`shrink-0 w-3.5 text-center ${
                    isDone
                      ? "text-success"
                      : isActive
                        ? "text-primary"
                        : "text-text-muted"
                  }`}
                >
                  {isDone ? "✓" : isActive ? "●" : "○"}
                </span>
                <span
                  className={
                    isDone
                      ? "text-text-secondary"
                      : isActive
                        ? "text-text-primary font-medium"
                        : "text-text-muted"
                  }
                >
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

interface ReviewActivitySectionProps {
  activity: PhaseReviewItem[];
  onOpenReviewModal: (attempt: number) => void;
}

function tryParseProcessingData(content: string | null): ProcessingData | null {
  if (!content) return null;
  try {
    const parsed = JSON.parse(content);
    if (parsed && typeof parsed === "object" && "findings" in parsed) {
      return parsed as ProcessingData;
    }
  } catch { /* not JSON */ }
  return null;
}

function ReviewActivitySection({ activity, onOpenReviewModal }: ReviewActivitySectionProps) {
  const [expandedAttempts, setExpandedAttempts] = useState<Set<number>>(new Set());

  const toggleExpand = (attempt: number) => {
    setExpandedAttempts((prev) => {
      const next = new Set(prev);
      if (next.has(attempt)) next.delete(attempt);
      else next.add(attempt);
      return next;
    });
  };

  return (
    <div className="space-y-2">
      {activity.map((item) => {
        const isExpanded = expandedAttempts.has(item.attempt);
        const processingData = item.phase === "processing" ? tryParseProcessingData(item.generated_content) : null;

        return (
          <div key={item.attempt} className="rounded-lg border border-border bg-surface overflow-hidden">
            {/* Header row */}
            <div className="flex items-stretch">
              <button
                type="button"
                onClick={() => onOpenReviewModal(item.attempt)}
                className="flex-1 px-3 py-2 space-y-1 text-left transition-colors hover:bg-primary-subtle"
              >
                <div className="flex items-center justify-between">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-text-muted">
                    Attempt {item.attempt}
                  </p>
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                      item.reviewer_approved
                        ? "bg-success-subtle text-success-text"
                        : "bg-error-subtle text-error-text"
                    }`}
                  >
                    {item.reviewer_approved ? "Approved" : "Rejected"}
                  </span>
                </div>
                {item.sources_used.length > 0 && (
                  <p className="text-xs text-text-secondary truncate">
                    <span className="font-medium text-text-primary">Sources: </span>
                    {item.sources_used.join(", ")}
                  </p>
                )}
                {item.sources_used.length === 0 && (
                  <p className="text-xs text-text-secondary capitalize">{item.phase} phase</p>
                )}
              </button>
              {processingData && (
                <button
                  type="button"
                  onClick={() => toggleExpand(item.attempt)}
                  className="shrink-0 border-l border-border px-2 text-text-muted hover:bg-primary-subtle hover:text-primary transition-colors"
                  aria-label={isExpanded ? "Collapse" : "Expand"}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform ${isExpanded ? "rotate-180" : ""}`}>
                    <path d="M6 9l6 6 6-6" />
                  </svg>
                </button>
              )}
            </div>
            {/* Inline parsed processing content */}
            {isExpanded && processingData && (
              <div className="border-t border-border px-3 py-2 space-y-2 bg-surface-muted/50">
                {processingData.findings && processingData.findings.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted">
                      Findings ({processingData.findings.length})
                    </p>
                    {[...processingData.findings]
                      .sort((a, b) => b.confidence - a.confidence)
                      .map((f, idx) => (
                        <div key={f.id ?? idx} className="rounded border border-border bg-surface p-2 space-y-1">
                          <div className="flex items-start justify-between gap-1">
                            <p className="text-[11px] font-semibold text-text-primary leading-snug flex-1">{f.title}</p>
                            {f.confidence != null && (
                              <span className={`shrink-0 rounded px-1 py-0.5 text-[10px] font-semibold ${
                                f.confidence >= 0.7 ? "bg-success-subtle text-success-text" :
                                f.confidence >= 0.4 ? "bg-warning-subtle text-warning-text" :
                                "bg-error-subtle text-error-text"
                              }`}>
                                {Math.round(f.confidence * 100)}%
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-text-secondary leading-relaxed">{f.finding}</p>
                        </div>
                      ))}
                  </div>
                )}
                {processingData.gaps && processingData.gaps.length > 0 && (
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-1">
                      Gaps ({processingData.gaps.length})
                    </p>
                    <ul className="space-y-0.5">
                      {processingData.gaps.map((gap, i) => (
                        <li key={i} className="flex gap-1.5 text-[11px] text-text-secondary">
                          <span className="shrink-0 text-text-muted">·</span>
                          <span>{gap}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
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
  const t = useT();
  return (
    <div>
      <button
        onClick={onOpenFileUpload}
        className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-xs font-medium text-text-secondary transition-colors hover:border-primary hover:bg-primary-subtle hover:text-primary"
      >
        {t.uploadFiles}
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
                  aria-label={t.removeFile(file.filename)}
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
              {showAllFiles ? t.showLess : t.showMore(hiddenCount)}
            </button>
          )}
        </>
      )}
    </div>
  );
}
