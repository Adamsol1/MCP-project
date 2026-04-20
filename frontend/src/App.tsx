import { useEffect, useMemo, useRef, useState } from "react";
import ChatWindow from "./components/ChatWindow/ChatWindow";
import { Sidebar } from "./components/Sidebar/Sidebar";
import { FileUploadModal } from "./components/FileUploadModal/FileUploadModal";
import { SettingsModal } from "./components/SettingsModal/SettingsModal";
import { useToast } from "./hooks/useToast/useToast";
import {
  deleteUploadedFile,
  listUploadedFiles,
  uploadFile,
  type UploadedFileRecord,
} from "./services/upload/upload";
import {
  getCollectionStatus,
  type CollectionStatus,
} from "./services/dialogue/dialogue";
import { useChat } from "./hooks/useChat/useChat";
import { useConversation } from "./hooks/useConversation/useConversation";
import {
  WorkspaceProvider,
  useWorkspace,
} from "./contexts/WorkspaceContext/WorkspaceContext";
import IntelligencePanel from "./components/IntelligencePanel/IntelligencePanel";
import StageTracker from "./components/StageTracker/StageTracker";
import { useT } from "./i18n/useT";
import { ToastContainer } from "./components/Toast";

const SIDEBAR_CONTENT_REVEAL_DELAY_MS = 180;

function WorkspaceResetWatcher({
  conversationId,
}: {
  conversationId: string | null;
}) {
  const { setPirData, setCollectionData, setHighlightedRefs, setReviewActivity } = useWorkspace();

  useEffect(() => {
    setPirData(null);
    setCollectionData(null);
    setHighlightedRefs([]);
    setReviewActivity([]);
  }, [conversationId]); // eslint-disable-line react-hooks/exhaustive-deps

  return null;
}

function AppShell() {
  const t = useT();
  const { success, error } = useToast();
  const {
    conversations,
    activeConversation,
    createNewConversation,
    switchConversation,
    deleteConversation,
    deleteAllConversations,
    renameConversation,
    updatePerspectives,
  } = useConversation();
  const [pendingPerspectives, setPendingPerspectives] = useState<string[]>([
    "NEUTRAL",
  ]);

  const {
    messages,
    sendMessage,
    isConfirming,
    stage,
    subState,
    isLoading,
    isSourceSelecting,
    isCollecting,
    availableSources,
    selectedSources,
    approve,
    reject,
    gatherMore,
    gatherMoreFromProcessing,
    toggleSourceSelection,
    submitSourceSelection,
    debugConfirm,
    devSnapshots,
    isDevSnapshotsLoading,
    refreshDevSnapshots,
    restoreDevSnapshot,
    devPrefill,
    triggerDevMessage,
    clearDevPrefill,
    inputPrefill,
    prefillGapPrompt,
    clearInputPrefill,
  } = useChat(pendingPerspectives);

  const [isCollapsed, setIsCollapsed] = useState(false);
  const [showExpandedContent, setShowExpandedContent] = useState(true);
  const [isRightPanelCollapsed, setIsRightPanelCollapsed] = useState(false);
  const revealTimeoutRef = useRef<ReturnType<typeof window.setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (revealTimeoutRef.current !== null) {
        window.clearTimeout(revealTimeoutRef.current);
      }
    };
  }, []);

  const handleToggleSidebar = () => {
    if (revealTimeoutRef.current !== null) {
      window.clearTimeout(revealTimeoutRef.current);
      revealTimeoutRef.current = null;
    }
    setIsCollapsed((prev) => {
      const next = !prev;
      if (next) {
        setShowExpandedContent(false);
      } else {
        revealTimeoutRef.current = window.setTimeout(() => {
          setShowExpandedContent(true);
          revealTimeoutRef.current = null;
        }, SIDEBAR_CONTENT_REVEAL_DELAY_MS);
      }
      return next;
    });
  };

  const [isFileUploadOpen, setIsFileUploadOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileRecord[]>([]);
  const [collectionStatus, setCollectionStatus] =
    useState<CollectionStatus | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{
    current: number;
    total: number;
  }>({ current: 0, total: 0 });
  const ensureConversationSession = () => {
    return activeConversation ?? createNewConversation(pendingPerspectives);
  };

  useEffect(() => {
    if (!activeConversation?.sessionId) return;

    let active = true;

    const loadFiles = async () => {
      try {
        const files = await listUploadedFiles(activeConversation.sessionId);
        if (active) {
          setUploadedFiles(files);
        }
      } catch (loadError) {
        console.error("Load uploads error:", loadError);
        if (active) {
          error("Failed to load uploaded files");
        }
      }
    };

    void loadFiles();

    return () => {
      active = false;
    };
  }, [activeConversation?.sessionId, error]);

  useEffect(() => {
    if (!isCollecting || !activeConversation?.sessionId) return;

    const sessionId = activeConversation.sessionId;
    let active = true;

    const poll = async () => {
      const status = await getCollectionStatus(sessionId);
      if (active) setCollectionStatus(status);
    };

    poll();

    const interval = setInterval(poll, 1500);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [isCollecting, activeConversation?.sessionId]);

  const visibleUploadedFiles = useMemo(
    () => (activeConversation?.sessionId ? uploadedFiles : []),
    [activeConversation?.sessionId, uploadedFiles],
  );
  const visibleCollectionStatus = isCollecting ? collectionStatus : null;

  const handleSubmit = async (files: File[]) => {
    const conversation = ensureConversationSession();

    setIsUploading(true);
    setUploadProgress({ current: 0, total: files.length });

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      try {
        const result = await uploadFile(file, conversation.sessionId);
        console.log("Upload result:", result);
        success(`Successfully uploaded ${file.name}`);
      } catch (uploadError) {
        console.error("Upload error:", uploadError);
        error(`Failed to upload ${file.name}`);
      }
      setUploadProgress({ current: i + 1, total: files.length });
    }

    const refreshedFiles = await listUploadedFiles(conversation.sessionId);
    setUploadedFiles(refreshedFiles);
    setIsUploading(false);
    setUploadProgress({ current: 0, total: 0 });
    setIsFileUploadOpen(false);
  };

  const handleFileRemove = async (file: UploadedFileRecord) => {
    if (!activeConversation?.sessionId) {
      return;
    }

    try {
      await deleteUploadedFile(
        activeConversation.sessionId,
        file.file_upload_id,
      );
      setUploadedFiles((prev) =>
        prev.filter((item) => item.file_upload_id !== file.file_upload_id),
      );
      success(`Removed ${file.filename}`);
    } catch (deleteError) {
      console.error("Delete upload error:", deleteError);
      error(`Failed to remove ${file.filename}`);
    }
  };

  const activePhase = activeConversation?.phase ?? "direction";

  return (
    <>
      <WorkspaceResetWatcher conversationId={activeConversation?.id ?? null} />

      <div className="flex flex-col h-screen">
        {/* Full-width top bar — spans all columns */}
        <div className="shrink-0 h-14 relative flex items-center bg-surface border-b border-border">
          {/* Left icon group — collapse toggle + settings, fixed so they never shift */}
          <div className="absolute left-3 top-1/2 -translate-y-1/2 z-10 flex items-center gap-1">
            <button
              aria-label={t.toggleSidebar}
              onClick={handleToggleSidebar}
              className="p-2 flex items-center justify-center hover:bg-surface-elevated rounded text-text-muted hover:text-text-primary"
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 18 18"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <rect x="1.5" y="1.5" width="15" height="15" rx="2" />
                <path d="M6 1.5v15" />
              </svg>
            </button>
            <button
              aria-label={t.openSettings}
              onClick={() => setIsSettingsOpen(true)}
              className="p-2 flex items-center justify-center hover:bg-surface-elevated rounded text-text-muted hover:text-text-primary"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                aria-hidden="true">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </button>
          </div>
          {/* Stage tracker — absolutely centered on the full bar */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="pointer-events-auto">
              <StageTracker activePhase={activePhase} />
            </div>
          </div>
          {/* Right panel toggle — top-right */}
          <div className="absolute right-3 top-1/2 -translate-y-1/2 z-10">
            <button
              aria-label="Toggle intelligence panel"
              onClick={() => setIsRightPanelCollapsed((v) => !v)}
              className="p-2 flex items-center justify-center hover:bg-surface-elevated rounded text-text-muted hover:text-text-primary"
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 18 18"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <rect x="1.5" y="1.5" width="15" height="15" rx="2" />
                <path d="M12 1.5v15" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content row — all panels live below the top bar */}
        <div className="flex flex-1 min-h-0 overflow-hidden">
          <Sidebar
            conversations={conversations}
            activeConversationId={activeConversation?.id ?? null}
            onNewChat={() => createNewConversation(pendingPerspectives)}
            onSwitchConversation={switchConversation}
            onDeleteConversation={deleteConversation}
            onRenameConversation={renameConversation}
            onDeleteAllConversations={deleteAllConversations}
            onDevSendMessage={() =>
              triggerDevMessage(
                "What are the latest cyber threats targeting European critical infrastructure?",
              )
            }
            onDevShowCollectionApproval={debugConfirm}
            devSnapshots={devSnapshots}
            isDevSnapshotsLoading={isDevSnapshotsLoading}
            onDevRefreshSnapshots={refreshDevSnapshots}
            onDevRestoreSnapshot={restoreDevSnapshot}
            isCollapsed={isCollapsed}
            showExpandedContent={showExpandedContent}
          />

          <main className="flex-1 min-h-0 flex flex-col bg-surface-elevated overflow-hidden">
            <ChatWindow
            messages={messages}
            onSendMessage={sendMessage}
            isConfirming={isConfirming}
            stage={stage}
            phase={activePhase}
            subState={subState}
            isLoading={isLoading}
            onApprove={approve}
            onReject={reject}
            onGatherMore={gatherMore}
            onGatherMoreFromProcessing={gatherMoreFromProcessing}
            isSourceSelecting={isSourceSelecting}
            isCollecting={isCollecting}
            collectionStatus={visibleCollectionStatus}
            availableSources={availableSources}
            selectedSources={selectedSources}
            onToggleSourceSelection={toggleSourceSelection}
            onSubmitSourceSelection={submitSourceSelection}
            devPrefill={devPrefill}
            onDevPrefillConsumed={clearDevPrefill}
            inputPrefill={inputPrefill}
            onInputPrefillConsumed={clearInputPrefill}
            onGapCollect={prefillGapPrompt}
          />
        </main>

        <div className={`bg-surface border-l border-border-muted flex flex-col overflow-hidden transition-all duration-200 ${isRightPanelCollapsed ? "w-0 border-l-0" : "w-72"}`}>
          <IntelligencePanel
            phase={activePhase}
            selectedPerspectives={
              activeConversation?.perspectives ?? pendingPerspectives
            }
            onPerspectiveChange={
              activeConversation
                ? updatePerspectives
                : setPendingPerspectives
            }
            onOpenFileUpload={() => setIsFileUploadOpen(true)}
            uploadedFiles={visibleUploadedFiles}
            onFileRemove={handleFileRemove}
            isCollecting={isCollecting}
            collectionStatus={visibleCollectionStatus}
          />
        </div>
        </div>{/* end content row */}
      </div>{/* end flex-col h-screen */}

      <FileUploadModal
        isOpen={isFileUploadOpen}
        onClose={() => setIsFileUploadOpen(false)}
        onSubmit={handleSubmit}
        isUploading={isUploading}
        uploadProgress={uploadProgress}
      />

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
      <ToastContainer position="top-right" />
    </>
  );
}

function App() {
  return (
    <WorkspaceProvider>
      <AppShell />
    </WorkspaceProvider>
  );
}

export default App;
