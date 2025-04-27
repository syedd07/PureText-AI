
import { useState, useCallback } from 'react';
import { Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface FileUploaderProps {
  onFileSelect: (file: File) => void;
}

const FileUploader = ({ onFileSelect }: FileUploaderProps) => {
  const [isDragging, setIsDragging] = useState(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragging(true);
    } else if (e.type === "dragleave") {
      setIsDragging(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type === "application/pdf" || 
          file.type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document" || 
          file.type === "text/plain") {
        onFileSelect(file);
      }
    }
  }, [onFileSelect]);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onFileSelect(files[0]);
    }
  };

  return (
    <div
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      className={`w-full p-8 border-2 border-dashed rounded-lg text-center transition-colors ${
        isDragging ? 'border-primary bg-primary/5' : 'border-gray-300'
      }`}
    >
      <Upload className="mx-auto h-12 w-12 text-gray-400" />
      <p className="mt-4 text-sm text-gray-600">
        Drag and drop your file here, or
      </p>
      <Button
        variant="outline"
        className="mt-4"
        onClick={() => document.getElementById('fileInput')?.click()}
      >
        Choose File
      </Button>
      <input
        id="fileInput"
        type="file"
        className="hidden"
        accept=".pdf,.docx,.txt"
        onChange={handleFileInput}
      />
      <p className="mt-2 text-xs text-gray-500">
        Supported formats: PDF, DOCX, TXT
      </p>
    </div>
  );
};

export default FileUploader;
