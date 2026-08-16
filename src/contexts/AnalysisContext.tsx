import React, { createContext, useContext, useState, useCallback } from 'react';
import type { AnalysisStage, AnalysisStatus } from '../types';
import { ANALYSIS_STAGES } from '../constants/mockData';

interface AnalysisContextType {
  stages: AnalysisStage[];
  status: AnalysisStatus;
  jobId: string | null;
  reportId: string | null;
  fileName: string | null;
  previewUrl: string | null;
  selectedFile: File | null;
  setStages: (stages: AnalysisStage[]) => void;
  setStatus: (status: AnalysisStatus) => void;
  setJobId: (id: string | null) => void;
  setReportId: (id: string | null) => void;
  setFileName: (name: string | null) => void;
  setPreviewUrl: (url: string | null) => void;
  setSelectedFile: (file: File | null) => void;
  resetAnalysis: () => void;
}

const AnalysisContext = createContext<AnalysisContextType | null>(null);

export const AnalysisProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [stages, setStages] = useState<AnalysisStage[]>(ANALYSIS_STAGES.map(s => ({ ...s })));
  const [status, setStatus] = useState<AnalysisStatus>('idle');
  const [jobId, setJobId] = useState<string | null>(null);
  const [reportId, setReportId] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const resetAnalysis = useCallback(() => {
    setStages(ANALYSIS_STAGES.map(s => ({ ...s })));
    setStatus('idle');
    setJobId(null);
    setReportId(null);
    setFileName(null);
    setPreviewUrl(null);
    setSelectedFile(null);
  }, []);

  return (
    <AnalysisContext.Provider value={{
      stages, setStages,
      status, setStatus,
      jobId, setJobId,
      reportId, setReportId,
      fileName, setFileName,
      previewUrl, setPreviewUrl,
      selectedFile, setSelectedFile,
      resetAnalysis,
    }}>
      {children}
    </AnalysisContext.Provider>
  );
};

export const useAnalysisContext = (): AnalysisContextType => {
  const ctx = useContext(AnalysisContext);
  if (!ctx) throw new Error('useAnalysisContext must be used within AnalysisProvider');
  return ctx;
};
