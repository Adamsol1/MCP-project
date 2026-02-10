import FileUpload from "./components/FileUpload/FileUpload";
import ChatWindow from "./components/ChatWindow/ChatWindow";
import { ToastContainer } from "./components/Toast";
import { useToast } from "./hooks/useToast";
import { uploadFile } from "./services/upload";
import { useChat } from "./hooks/useChat";

function App() {
  const { success, error } = useToast();
  const { messages, sendMessage } = useChat();

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
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <ToastContainer position="top-right" />
      <div className="w-[50vw] mx-auto text-center">
        <h1 className="text-4xl font-bold text-gray-900">MCP Project</h1>
        <ChatWindow messages={messages} onSendMessage={sendMessage} />
        <FileUpload onFileSelect={handleFileSelect} onSubmit={handleSubmit} />
      </div>
    </div>
  );
}

export default App;
