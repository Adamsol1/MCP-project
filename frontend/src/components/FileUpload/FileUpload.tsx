import { useState } from "react";

interface FileUploadProps {
  onFileSelect?: (file: File) => void;
  onSubmit?: (files: File[]) => void;
}

export default function FileUpload({
  onFileSelect,
  onSubmit,
}: FileUploadProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  /**
   * Handles file input change event
   * @param event
   */
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
    event.target.value = ""; // Reset the input value to allow re-uploading the same file
  };

  /**
   * Prevent default beheaviour from browser when file is dragged over dropzone
   * @param event
   */
  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault(); // Prevent default browser behavior
  };

  /**
   * Handle file drop event with multiple files support
   * @param event
   */
  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault(); // Prevent default browser behavior
    const files = event.dataTransfer.files;
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

  const handleCancel = () => {
    setSelectedFiles([]);
  };

  const handleSubmit = () => {
    if (onSubmit) {
      onSubmit(selectedFiles);
    }
  };

  /**
   * Function that formats file size into human-readable string
   * @param bytes - Bytes size of the file in numbers
   * @returns {string} size - String of file size in bytes, KB, or MB
   */
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} bytes`;
    else if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    else return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  /**
   * Handles remove of file listed
   * @param fileToRemove
   */
  const handleRemove = (fileToRemove: File) => {
    setSelectedFiles((prev) => prev.filter((file) => file !== fileToRemove));
  };

  return (
    <div className="w-full  mx-auto p-4">
      {/* Drop Zone */}
      <div
        data-testid="file-dropzone"
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        className="relative border-2 border-dashed p-42 border-gray-300 rounded-lg min-h-64 text-center hover:border-blue-400 transition-colors cursor-pointer"
      >
        <label
          htmlFor="file-upload"
          className="absolute inset-0 flex items-center justify-center cursor-pointer"
        >
          <span className="sr-only">Upload File</span>
          <div className="text-gray-500">
            <p className="text-2xl font-normal">Drag & drop files here</p>
            <p className="text-md">or click to browse</p>
            <p className="text-sm mt-2 text-gray-400">
              Supported: .json, .csv, .pdf, .txt
            </p>
          </div>
        </label>
        <input
          id="file-upload"
          type="file"
          accept=".json, .csv, .pdf, .txt"
          onChange={handleFileChange}
          multiple={true}
          className="hidden"
        />
      </div>

      {/* File List */}
      {selectedFiles.length > 0 && (
        <div className="mt-4 space-y-2">
          {selectedFiles.map((file) => (
            <div
              key={file.name}
              className="flex items-center justify-between bg-gray-50 p-3 rounded-lg"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-700 truncate">
                  {file.name}
                </p>
                <p className="text-xs text-gray-500">
                  {formatFileSize(file.size)}
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleRemove(file)}
                className="ml-4 text-red-500 hover:text-red-700 text-sm font-medium"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Action Buttons */}
      <div className="mt-6 flex gap-3 justify-end">
        <button
          type="button"
          onClick={handleCancel}
          className="px-4 py-2 text-gray-600 hover:text-gray-800 font-medium"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSubmit}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 font-medium"
        >
          Submit
        </button>
      </div>
    </div>
  );
}
