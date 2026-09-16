import { ANALYSIS_STAGES } from '../constants/mockData';
import { createDynamicReport, reportService } from './reportService';
import { analyzeImageFile } from './imageForensicAnalyzer';
import { recordCompletedScan } from './dashboardStore';
import type { AnalysisStage, ForensicReport } from '../types';

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const analysisService = {
  async runAnalysis(
    _jobId: string,
    file: File | null,
    onStageUpdate: (stages: AnalysisStage[]) => void
  ): Promise<string> {
    const stages = ANALYSIS_STAGES.map(s => ({ ...s }));

    // Progress through pipeline animation smoothly
    for (let i = 0; i < stages.length; i++) {
      stages[i].status = 'active';
      stages[i].progress = 0;
      onStageUpdate([...stages]);

      const stageTime = 50 + Math.random() * 80;
      for (let p = 0; p <= 100; p += 25) {
        await delay(stageTime);
        stages[i].progress = Math.min(p, 100);
        onStageUpdate([...stages]);
      }

      stages[i].status = 'completed';
      stages[i].progress = 100;
      onStageUpdate([...stages]);

      await delay(60);
    }

    let report: ForensicReport;

    if (file) {
      const isVideo = file.type.startsWith('video/') || /\.(mp4|avi|mov|mkv|webm)$/i.test(file.name);

      // Call the unified Biometric Liveness & Forensics FastAPI backend
      try {
        const formData = new FormData();
        formData.append('file', file);

        // Videos take longer for rPPG pulse extraction, allow up to 45s; images up to 15s
        const controller = new AbortController();
        const timeoutMs = isVideo ? 45000 : 15000;
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

        const res = await fetch('http://localhost:8000/api/v1/analyze', {
          method: 'POST',
          body: formData,
          signal: controller.signal,
        });
        clearTimeout(timeoutId);

        if (res.ok) {
          const json = await res.json();
          if (json.success && json.report) {
            report = json.report;

            // Preserve local image preview if available
            const uploadedImg = sessionStorage.getItem('current_upload_img');
            if (uploadedImg && (!report.explainableAI || !report.explainableAI.imageUrl)) {
              report.explainableAI = {
                ...(report.explainableAI || { highRiskRegions: [] }),
                imageUrl: uploadedImg,
              };
            }
          } else {
            report = await analyzeImageFile(file);
          }
        } else {
          console.warn('Backend returned non-200 status, falling back to local analyzer');
          report = await analyzeImageFile(file);
        }
      } catch (err) {
        console.warn('Backend unavailable, using client-side forensic fallback:', err);
        report = await analyzeImageFile(file);
      }
    } else {
      const reportId = `RPT-${Math.floor(100000 + Math.random() * 900000)}`;
      report = createDynamicReport(reportId, 'media_scan.jpg');
    }

    await reportService.saveReport(report);

    recordCompletedScan({
      fileName: report.fileName,
      verdict: report.verdict,
      confidenceScore: report.confidenceScore,
      mediaType: report.mediaType,
      riskLevel: report.riskLevel,
      reportId: report.id,
    });

    return report.id;
  },
};
