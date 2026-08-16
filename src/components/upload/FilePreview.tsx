import React, { useState, useEffect } from 'react';
import { X, FileImage, FileVideo, CheckCircle2 } from 'lucide-react';
import { GlassCard } from '../common/GlassCard';
import { formatFileSize } from '../../utils/formatters';

interface FilePreviewProps {
  file: File;
  onRemove: () => void;
  onStartAnalysis: () => void;
}

export const FilePreview: React.FC<FilePreviewProps> = ({ file, onRemove, onStartAnalysis }) => {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const isVideo = file.type.startsWith('video/');

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  return (
    <GlassCard glow className="relative">
      <button
        onClick={onRemove}
        className="absolute top-4 right-4 z-10 w-8 h-8 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400 hover:text-white hover:bg-red-500/20 hover:border-red-500/40 transition-colors"
      >
        <X className="w-4 h-4" />
      </button>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
        {/* Media Preview Area */}
        <div className="relative rounded-xl overflow-hidden bg-slate-950 border border-slate-800 aspect-video flex items-center justify-center">
          {previewUrl && (
            isVideo ? (
              <video src={previewUrl} controls className="max-h-full max-w-full object-contain" />
            ) : (
              <img src={previewUrl} alt={file.name} className="max-h-full max-w-full object-contain" />
            )
          )}
          <div className="absolute top-3 left-3 bg-slate-900/80 backdrop-blur-md px-2.5 py-1 rounded-md text-xs font-mono text-cyan-400 border border-cyan-500/30 flex items-center gap-1.5">
            {isVideo ? <FileVideo className="w-3.5 h-3.5" /> : <FileImage className="w-3.5 h-3.5" />}
            <span>{isVideo ? 'VIDEO FILE' : 'IMAGE FILE'}</span>
          </div>
        </div>

        {/* File Metadata Info */}
        <div className="space-y-4">
          <div>
            <h3 className="text-xl font-bold text-white truncate">{file.name}</h3>
            <p className="text-slate-400 text-sm font-mono mt-1">
              Size: {formatFileSize(file.size)} | Type: {file.type || 'Unknown'}
            </p>
          </div>

          <div className="space-y-2 text-xs text-slate-300 font-mono bg-slate-900/50 p-4 rounded-xl border border-slate-800">
            <div className="flex justify-between py-1 border-b border-slate-800">
              <span className="text-slate-500">File Name:</span>
              <span className="truncate max-w-[200px] text-white">{file.name}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800">
              <span className="text-slate-500">Last Modified:</span>
              <span className="text-white">{new Date(file.lastModified).toLocaleDateString()}</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-500">Status:</span>
              <span className="text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Ready for scanning
              </span>
            </div>
          </div>

          <button
            onClick={onStartAnalysis}
            className="w-full btn-primary py-3.5 text-base rounded-xl font-semibold flex items-center justify-center gap-2 shadow-lg"
          >
            Initiate Forensic Pipeline
          </button>
        </div>
      </div>
    </GlassCard>
  );
};
