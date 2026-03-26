import { useEffect, useState } from "react";
import ChatWindow from "./components/ChatWindow/ChatWindow";
import { Sidebar } from "./components/Sidebar/Sidebar";
import { FileUploadModal } from "./components/FileUploadModal/FileUploadModal";
import { SettingsModal } from "./components/SettingsModal/SettingsModal";
import { useToast } from "./hooks/useToast";
import {
  deleteUploadedFile,
  listUploadedFiles,
  uploadFile,
  type UploadedFileRecord,
} from "./services/upload";
import {
  getCollectionStatus,
  type CollectionStatus,
} from "./services/dialogue";
import { useChat } from "./hooks/useChat";
import { useConversation } from "./hooks/useConversation";
import type { DialogueStage } from "./types/dialogue";
import { WorkspaceProvider, useWorkspace } from "./contexts/WorkspaceContext/WorkspaceContext";
import IntelligencePanel from "./components/IntelligencePanel/IntelligencePanel";

function WorkspaceResetWatcher({ conversationId }: { conversationId: string | null }) {
  const { setPirData, setActivePhase, setCollectionData, setHighlightedRefs } = useWorkspace();
  useEffect(() => {
    setPirData(null);
    setActivePhase("direction");
    setCollectionData(null);
    setHighlightedRefs([]);
  }, [conversationId]); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

function WorkspacePhaseWatcher({ isSourceSelecting }: { isSourceSelecting: boolean }) {
  const { setActivePhase } = useWorkspace();
  useEffect(() => {
    if (isSourceSelecting) setActivePhase("collection");
  }, [isSourceSelecting]); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

function App() {
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
  const [collectionStatus, setCollectionStatus] = useState<CollectionStatus | null>(null);

  const ensureConversationSession = () => {
    return activeConversation ?? createNewConversation();
  };

  const refreshUploadedFiles = async (sessionId: string) => {
    try {
      const files = await listUploadedFiles(sessionId);
      setUploadedFiles(files);
    } catch (loadError) {
      console.error("Load uploads error:", loadError);
      error("Failed to load uploaded files");
    }
  };

  useEffect(() => {
    if (!activeConversation?.sessionId) {
      setUploadedFiles([]);
      return;
    }
    refreshUploadedFiles(activeConversation.sessionId);
  }, [activeConversation?.sessionId]);

  useEffect(() => {
    if (!isCollecting || !activeConversation?.sessionId) {
      if (!isCollecting) setCollectionStatus(null);
      return;
    }
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

  const handleSubmit = async (files: File[]) => {
    const conversation = ensureConversationSession();

    for (const file of files) {
      try {
        const result = await uploadFile(file, conversation.sessionId);
        console.log("Upload result:", result);
        success(`Successfully uploaded ${file.name}`);
      } catch (uploadError) {
        console.error("Upload error:", uploadError);
        error(`Failed to upload ${file.name}`);
      }
    }

    await refreshUploadedFiles(conversation.sessionId);
    setIsFileUploadOpen(false);
  };

  const handleFileRemove = async (file: UploadedFileRecord) => {
    if (!activeConversation?.sessionId) {
      return;
    }

    try {
      await deleteUploadedFile(activeConversation.sessionId, file.file_upload_id);
      setUploadedFiles((prev) =>
        prev.filter((item) => item.file_upload_id !== file.file_upload_id),
      );
      success(`Removed ${file.filename}`);
    } catch (deleteError) {
      console.error("Delete upload error:", deleteError);
      error(`Failed to remove ${file.filename}`);
    }
  };

  return (
    <WorkspaceProvider>
    <WorkspaceResetWatcher conversationId={activeConversation?.id ?? null} />
    <WorkspacePhaseWatcher isSourceSelecting={isSourceSelecting} />
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
        onDevJumpToStage={(nextStage: DialogueStage) => jumpToDevStage(nextStage)}
        onDevSyncStage={syncDevStage}
        onDevResetStage={resetDevStage}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      <main className="flex-1 flex flex-col bg-surface-elevated mx-1">
        <ChatWindow
          messages={messages}
          onSendMessage={sendMessage}
          isConfirming={isConfirming}
          stage={stage}
          subState={subState}
          isLoading={isLoading}
          onApprove={approve}
          onReject={reject}
          onGatherMore={gatherMore}
          onGatherMoreFromProcessing={gatherMoreFromProcessing}
          isSourceSelecting={isSourceSelecting}
          isCollecting={isCollecting}
          collectionStatus={collectionStatus}
          availableSources={availableSources}
          selectedSources={selectedSources}
          onToggleSourceSelection={toggleSourceSelection}
          onSubmitSourceSelection={submitSourceSelection}
          devPrefill={devPrefill}
          onDevPrefillConsumed={clearDevPrefill}
        />
      </main>

      <div className="w-56 bg-surface border-l border-border-muted flex flex-col overflow-hidden">
        <IntelligencePanel
          selectedPerspectives={activeConversation?.perspectives ?? ["NEUTRAL"]}
          onPerspectiveChange={updatePerspectives}
          onOpenFileUpload={() => setIsFileUploadOpen(true)}
          uploadedFiles={uploadedFiles}
          onFileRemove={handleFileRemove}
          isCollecting={isCollecting}
          collectionStatus={collectionStatus}
        />
      </div>

      <FileUploadModal
        isOpen={isFileUploadOpen}
        onClose={() => setIsFileUploadOpen(false)}
        onSubmit={handleSubmit}
      />

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </div>
    </WorkspaceProvider>
  );
}

export default App;
