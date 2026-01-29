import { useState } from "react";

interface FileUploadProps {
  onFileSelect?: (file: File) => void;
}

export default function FileUpload({ onFileSelect }: FileUploadProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      const newFiles = Array.from(files);
      setSelectedFiles((prev) => [...prev, ...newFiles]);
      newFiles.forEach((file) => {
        if (onFileSelect) {
          onFileSelect(file);
        }
      });
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} bytes`;
    else if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    else return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const handleRemove = (fileToRemove: File) => {
    setSelectedFiles((prev) => prev.filter((file) => file !== fileToRemove));
  };

  return (
    <div>
      <label htmlFor="file-upload">Upload File</label>
      <input
        id="file-upload"
        type="file"
        accept=".json, .csv, .pdf, .txt"
        onChange={handleFileChange}
        multiple={true}
      />
      {selectedFiles.map((file) => (
        <div key={file.name}>
          <span>{file.name}</span>
          <span>{formatFileSize(file.size)}</span>
          <button type="button" onClick={() => handleRemove(file)}>
            Remove
          </button>
        </div>
      ))}
    </div>
  );
}
