import { useState } from "react";
import ChatWindow from "./components/ChatWindow/ChatWindow";
import { Sidebar } from "./components/Sidebar/Sidebar";
import { OptionsPanel } from "./components/OptionsPanel/OptionsPanel";
import { FileUploadModal } from "./components/FileUploadModal/FileUploadModal";
import { SettingsModal } from "./components/SettingsModal/SettingsModal";
import { useToast } from "./hooks/useToast";
import { uploadFile } from "./services/upload";
import { useChat } from "./hooks/useChat";
import { useConversation } from "./hooks/useConversation";
import type { DialogueStage } from "./types/dialogue";

/**
 * Root application component.
 *
 * Composes the full-screen three-column layout:
 *   Sidebar (left) | ChatWindow (centre, flex-1) | OptionsPanel (right)
 *
 * Also owns the FileUploadModal overlay and wires together the file-upload flow:
 *   1. User opens the modal via the OptionsPanel "Upload Files" button.
 *   2. User selects files and clicks Submit.
 *   3. handleSubmit uploads each file sequentially via the upload service and
 *      fires a success or error toast for each result.
 *   4. The modal closes after all uploads complete (or fail).
 *
 * All conversation and chat state is delegated to useConversation and useChat.
 * App only passes the slices and callbacks that each child component needs,
 * keeping the child components decoupled from the global state shape.
 */
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
    isLoading,
    approve,
    reject,
    debugConfirm,
    jumpToDevStage,
    syncDevStage,
    resetDevStage,
    devPrefill,
    triggerDevMessage,
    clearDevPrefill,
  } = useChat();

  /** Controls the visibility of the FileUploadModal overlay. */
  const [isFileUploadOpen, setIsFileUploadOpen] = useState(false);
  /** Controls the visibility of the SettingsModal overlay. */
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  /**
   * Tracks files that have been successfully uploaded via the FileUploadModal.
   * Shown as a collapsible list in the OptionsPanel so the user can see what
   * data sources are available to the current session.
   */
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  /**
   * Uploads all queued files sequentially, shows a toast for each result, and
   * appends each successfully uploaded file to the uploadedFiles list so it
   * appears in the OptionsPanel. Closes the modal once the loop completes.
   *
   * @param files - The list of File objects the user submitted.
   */
  const handleSubmit = async (files: File[]) => {
    for (const file of files) {
      try {
        const result = await uploadFile(file);
        console.log("Upload result:", result);
        success(`Successfully uploaded ${file.name}`);
        setUploadedFiles((prev) => [...prev, file]);
      } catch (err) {
        console.error("Upload error:", err);
        error(`Failed to upload ${file.name}`);
      }
    }
    setIsFileUploadOpen(false);
  };

  /**
   * Removes a file from the uploaded files list shown in the OptionsPanel.
   * This is a client-side-only operation — the file remains on the backend.
   *
   * @param file - The File object to remove from the display list.
   */
  const handleFileRemove = (file: File) => {
    setUploadedFiles((prev) => prev.filter((f) => f !== file));
  };

  return (
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
            "What are the latest cyber threats targeting European critical infrastructure?"
          )
        }
        onDevShowCollectionApproval={debugConfirm}
        onDevJumpToStage={(stage: DialogueStage) => jumpToDevStage(stage)}
        onDevSyncStage={syncDevStage}
        onDevResetStage={resetDevStage}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      {/* mx-1 creates a slim visible gap between the sidebars and the chat area. */}
      <main className="flex-1 flex flex-col bg-surface-elevated mx-1">
        <ChatWindow
          messages={messages}
          onSendMessage={sendMessage}
          isConfirming={isConfirming}
          stage={stage}
          isLoading={isLoading}
          onApprove={approve}
          onReject={reject}
          devPrefill={devPrefill}
          onDevPrefillConsumed={clearDevPrefill}
        />
      </main>

      <OptionsPanel
        selectedPerspectives={activeConversation?.perspectives ?? ["NEUTRAL"]}
        onPerspectiveChange={updatePerspectives}
        onOpenFileUpload={() => setIsFileUploadOpen(true)}
        uploadedFiles={uploadedFiles}
        onFileRemove={handleFileRemove}
        stage={stage}
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
  );
}

export default App;
