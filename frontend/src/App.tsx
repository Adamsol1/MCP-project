import { useEffect, useMemo, useState } from "react";
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

function WorkspaceResetWatcher({
  conversationId,
}: {
  conversationId: string | null;
}) {
  const { setPirData, setCollectionData, setHighlightedRefs } = useWorkspace();

  useEffect(() => {
    setPirData(null);
    setCollectionData(null);
    setHighlightedRefs([]);
  }, [conversationId]); // eslint-disable-line react-hooks/exhaustive-deps

  return null;
}

function AppShell() {
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
    jumpToDevStage,
    syncDevStage,
    resetDevStage,
    devPrefill,
    triggerDevMessage,
    clearDevPrefill,
  } = useChat();

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
    return activeConversation ?? createNewConversation();
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
  const isAnalysisPhase = activePhase === "analysis";

  return (
    <>
      <WorkspaceResetWatcher conversationId={activeConversation?.id ?? null} />

      <div className="flex h-screen">
        <Sidebar
          conversations={conversations}
          activeConversationId={activeConversation?.id ?? null}
          onNewChat={createNewConversation}
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
          onDevJumpToStage={jumpToDevStage}
          onDevSyncStage={syncDevStage}
          onDevResetStage={resetDevStage}
          onOpenSettings={() => setIsSettingsOpen(true)}
        />

        <main className="flex-1 min-h-0 flex flex-col bg-surface-elevated overflow-hidden">
          <StageTracker activePhase={activePhase} />
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
          />
        </main>

        {!isAnalysisPhase && (
          <div className="w-72 bg-surface border-l border-border-muted flex flex-col overflow-hidden">
            <IntelligencePanel
              phase={activePhase}
              selectedPerspectives={
                activeConversation?.perspectives ?? ["NEUTRAL"]
              }
              onPerspectiveChange={updatePerspectives}
              onOpenFileUpload={() => setIsFileUploadOpen(true)}
              uploadedFiles={visibleUploadedFiles}
              onFileRemove={handleFileRemove}
              isCollecting={isCollecting}
              collectionStatus={visibleCollectionStatus}
            />
          </div>
        )}
      </div>

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
