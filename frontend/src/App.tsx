import FileUpload from "./components/FileUpload/FileUpload";
function App() {
  const handleFileSelect = (file: File) => {
    console.log("Selected file:", file.name);
  };

  const handleSubmit = (files: File[]) => {
    console.log(
      "Submitted files:",
      files.map((file) => file.name),
    );
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900">MCP Project</h1>
        <FileUpload onFileSelect={handleFileSelect} onSubmit={handleSubmit} />
      </div>
    </div>
  );
}

export default App;
