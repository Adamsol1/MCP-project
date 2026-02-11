import { useState } from "react";
import FileUpload from "./components/FileUpload/FileUpload";
import ChatWindow from "./components/ChatWindow/ChatWindow";
import PerspectiveSelector from "./components/PerspectiveSelector/PerspectiveSelector";
import { ToastContainer } from "./components/Toast";
import { useToast } from "./hooks/useToast";
import { uploadFile } from "./services/upload";
import { useChat } from "./hooks/useChat";

function App() {
  const { success, error } = useToast();
  const { messages, sendMessage } = useChat();
  const [selectedPerspectives, setSelectedPerspectives] = useState<string[]>(["NEUTRAL"]);

  const handleFileSelect = (file: File) => {
    console.log("Selected file:", file.name);
  };

  const handleSubmit = async (files: File[]) => {
    for (const file of files) {
      try {
        const result = await uploadFile(file);
        console.log("Upload result:", result);
        success(`Successfully uploaded ${file.name}`);
      } catch (err) {
        console.error("Upload error:", err);
        error(`Failed to upload ${file.name}`);
      }
    }
  };

  return (
    <div className="relative min-h-screen bg-gray-100 flex flex-col items-center">
      <ToastContainer position="top-right" />
      <h1 className="text-4xl font-bold text-gray-900 mt-8 mb-6">MCP Project</h1>
      <div className="w-[50vw]">
        <ChatWindow messages={messages} onSendMessage={sendMessage} />
        <FileUpload onFileSelect={handleFileSelect} onSubmit={handleSubmit} />
      </div>
      <div className="fixed right-6 top-24">
        <PerspectiveSelector
          selected={selectedPerspectives}
          onChange={setSelectedPerspectives}
        />
      </div>
    </div>
  );
}

export default App;
