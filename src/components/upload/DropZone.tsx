import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion } from 'framer-motion';
import { Upload, FileImage, FileVideo, AlertCircle } from 'lucide-react';

interface DropZoneProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
  error?: string | null;
}

export const DropZone: React.FC<DropZoneProps> = ({ onFileSelect, disabled = false, error }) => {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles && acceptedFiles.length > 0) {
        onFileSelect(acceptedFiles[0]);
      }
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    disabled,
    multiple: false,
    accept: {
      'image/*': [],
      'video/*': [],
    },
  });

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={`relative cursor-pointer rounded-2xl p-10 text-center transition-all duration-300 ${
          isDragActive
            ? 'border-2 border-cyan-400 bg-cyan-500/10 shadow-[0_0_30px_rgba(6,182,212,0.25)] scale-[1.01]'
            : isDragReject || error
            ? 'border-2 border-red-500/50 bg-red-500/10'
            : 'border-2 border-dashed border-slate-700/60 bg-slate-900/40 hover:border-cyan-500/40 hover:bg-slate-900/60'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} />

        {isDragActive && (
          <div className="absolute inset-0 overflow-hidden rounded-2xl pointer-events-none">
            <div className="w-full h-1 bg-gradient-to-r from-transparent via-cyan-400 to-transparent animate-scan-line" />
          </div>
        )}

        <div className="flex flex-col items-center justify-center space-y-4">
          <motion.div
            animate={isDragActive ? { scale: 1.1, y: -5 } : { scale: 1, y: 0 }}
            className={`w-16 h-16 rounded-2xl flex items-center justify-center ${
              isDragActive ? 'bg-cyan-500/20 text-cyan-400' : 'bg-slate-800 text-slate-400'
            }`}
          >
            <Upload className="w-8 h-8" />
          </motion.div>

          <div>
            <p className="text-lg font-semibold text-white">
              {isDragActive ? 'Drop media file here...' : 'Drag & drop image or video for forensic scan'}
            </p>
            <p className="text-slate-400 text-sm mt-1">
              or <span className="text-cyan-400 font-medium hover:underline">browse files</span> from your computer
            </p>
          </div>

          <div className="flex items-center gap-6 pt-2 text-xs text-slate-500 font-mono">
            <div className="flex items-center gap-1.5">
              <FileImage className="w-4 h-4 text-blue-400" />
              <span>Images (JPG, PNG, WebP, TIFF - max 50MB)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <FileVideo className="w-4 h-4 text-cyan-400" />
              <span>Videos (MP4, AVI, MOV - max 500MB)</span>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-2 mt-3 text-red-400 text-sm font-medium px-4 py-2 bg-red-500/10 border border-red-500/20 rounded-lg"
        >
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </motion.div>
      )}
    </div>
  );
};
