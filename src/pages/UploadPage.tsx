import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DropZone } from '../components/upload/DropZone';
import { FilePreview } from '../components/upload/FilePreview';
import { UploadProgress } from '../components/upload/UploadProgress';
import { useAnalysisContext } from '../contexts/AnalysisContext';
import { uploadService } from '../services/uploadService';
import { Shield, Info } from 'lucide-react';

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const { setJobId, setFileName, setPreviewUrl, setStatus, resetAnalysis, setSelectedFile: setContextFile } = useAnalysisContext();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  // Called when user drops / selects a file — show preview, do NOT auto-start
  const handleFileSelect = (file: File) => {
    const validation = uploadService.validateFile(file);
    if (!validation.valid) {
      setError(validation.error || 'Invalid file');
      setSelectedFile(null);
      return;
    }
    setError(null);
    setSelectedFile(file);
  };

  // Called when user clicks "Initiate Forensic Pipeline" in FilePreview
  const handleStartAnalysis = async () => {
    if (!selectedFile) return;

    resetAnalysis();
    setContextFile(selectedFile);
    setUploading(true);
    setFileName(selectedFile.name);
    setStatus('uploading');

    // Create object URL and base64 for persistent preview in HeatmapViewer
    const objUrl = URL.createObjectURL(selectedFile);
    setPreviewUrl(objUrl);

    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const base64 = reader.result as string;
        // sessionStorage has ~5MB limit — skip for large files (videos)
        if (base64.length < 4 * 1024 * 1024) {
          sessionStorage.setItem('current_upload_img', base64);
        } else {
          sessionStorage.removeItem('current_upload_img');
        }
      } catch {
        sessionStorage.removeItem('current_upload_img');
      }
    };
    reader.readAsDataURL(selectedFile);

    try {
      const res = await uploadService.uploadFile(selectedFile, (p) => setProgress(p));
      setJobId(res.jobId);
      setStatus('processing');
      navigate('/analysis');
    } catch (err) {
      setError('Upload failed. Please try again.');
      setStatus('error');
      setUploading(false);
    }
  };


  return (
    <div className="p-6 md:p-10 space-y-8 max-w-4xl mx-auto">
      <div>
        <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs mb-1">
          <Shield className="w-4 h-4" />
          <span>MEDIA INGESTION STAGE</span>
        </div>
        <h1 className="text-2xl md:text-3xl font-extrabold text-white">Upload Media For Forensic Scan</h1>
        <p className="text-slate-400 text-sm mt-1">
          Select an image or video file to run deepfake detection, frequency analysis, and metadata verification.
        </p>
      </div>

      {uploading ? (
        <UploadProgress progress={progress} fileName={selectedFile?.name || ''} />
      ) : selectedFile ? (
        /* Show FilePreview with video playback; user must click button to start */
        <FilePreview
          file={selectedFile}
          onRemove={() => { setSelectedFile(null); setError(null); }}
          onStartAnalysis={handleStartAnalysis}
        />
      ) : (
        <DropZone onFileSelect={handleFileSelect} error={error} />
      )}

      {/* Forensic Rules Box */}
      {!selectedFile && !uploading && (
        <div className="glass-card p-5 border border-slate-800 space-y-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <Info className="w-4 h-4 text-cyan-400" />
            <span>Forensic Processing Guidelines</span>
          </div>
          <ul className="text-xs text-slate-400 space-y-1.5 list-disc list-inside font-mono">
            <li>Supported Images: JPEG, PNG, WebP, TIFF, BMP (Max 50MB)</li>
            <li>Supported Videos: MP4, AVI, MOV, MKV (Max 500MB)</li>
            <li>Original files with uncompressed EXIF metadata yield higher confidence scores</li>
            <li>Files are processed in isolated memory and automatically purged post-analysis</li>
          </ul>
        </div>
      )}
    </div>
  );
};
