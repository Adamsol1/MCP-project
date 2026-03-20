import { useEffect, useState } from "react";
import ChatWindow from "./components/ChatWindow/ChatWindow";
import { Sidebar } from "./components/Sidebar/Sidebar";
import { OptionsPanel } from "./components/OptionsPanel/OptionsPanel";
import { FileUploadModal } from "./components/FileUploadModal/FileUploadModal";
import { SettingsModal } from "./components/SettingsModal/SettingsModal";
import { useToast } from "./hooks/useToast";
import {
  deleteUploadedFile,
  listUploadedFiles,
  uploadFile,
  type UploadedFileRecord,
} from "./services/upload";
import { useChat } from "./hooks/useChat";
import { useConversation } from "./hooks/useConversation";
import type { DialogueStage } from "./types/dialogue";
import { WorkspaceProvider, useWorkspace } from "./contexts/WorkspaceContext/WorkspaceContext";
import IntelligencePanel from "./components/IntelligencePanel/IntelligencePanel";
import { getWorkspacePhaseForDialogueStage } from "./services/workspacePhase";
import AnalysisPrototypeView from "./components/AnalysisPrototypeView/AnalysisPrototypeView";

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

function WorkspaceStageSync({ stage }: { stage: DialogueStage }) {
  const { setActivePhase } = useWorkspace();

  useEffect(() => {
    setActivePhase(getWorkspacePhaseForDialogueStage(stage));
  }, [stage, setActivePhase]);

  return null;
}

function AppShell() {
  const { success, error } = useToast();
  const { activePhase } = useWorkspace();
  const {
    conversations,
    activeConversation,
    createNewConversation,
    switchConversation,
    deleteConversation,
    deleteAllConversations,
    renameConversation,
    updatePerspectives,
    setStage,
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

  const openAnalysisDemo = () => {
    createNewConversation();
    setStage("complete", null);
  };

  const isAnalysisPhase = activePhase === "analysis";

  return (
    <>
      <WorkspaceResetWatcher conversationId={activeConversation?.id ?? null} />
      <WorkspaceStageSync stage={stage} />
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
          onDevOpenAnalysis={openAnalysisDemo}
          onDevJumpToStage={(nextStage: DialogueStage) => jumpToDevStage(nextStage)}
          onDevSyncStage={syncDevStage}
          onDevResetStage={resetDevStage}
          onOpenSettings={() => setIsSettingsOpen(true)}
        />

        <main className="flex-1 flex flex-col bg-surface-elevated mx-1 overflow-hidden">
          {isAnalysisPhase ? (
            <div className="flex-1 overflow-y-auto px-4 py-4 scrollbar-chatgpt">
              <section className="rounded-xl border border-border-muted bg-surface p-4 shadow-sm">
                <AnalysisPrototypeView />
              </section>
            </div>
          ) : (
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
              isSourceSelecting={isSourceSelecting}
              isCollecting={isCollecting}
              availableSources={availableSources}
              selectedSources={selectedSources}
              onToggleSourceSelection={toggleSourceSelection}
              onSubmitSourceSelection={submitSourceSelection}
              devPrefill={devPrefill}
              onDevPrefillConsumed={clearDevPrefill}
            />
          )}
        </main>

        {!isAnalysisPhase && (
          <div className="w-72 bg-surface border-l border-border-muted flex flex-col overflow-hidden">
            <IntelligencePanel />
          </div>
        )}

        <OptionsPanel
          selectedPerspectives={activeConversation?.perspectives ?? ["NEUTRAL"]}
          onPerspectiveChange={updatePerspectives}
          onOpenFileUpload={() => setIsFileUploadOpen(true)}
          uploadedFiles={uploadedFiles}
          onFileRemove={handleFileRemove}
        />

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
