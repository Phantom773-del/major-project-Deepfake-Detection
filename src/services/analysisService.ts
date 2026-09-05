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

    for (let i = 0; i < stages.length; i++) {
      stages[i].status = 'active';
      stages[i].progress = 0;
      onStageUpdate([...stages]);

      const stageTime = 60 + Math.random() * 100;
      for (let p = 0; p <= 100; p += 25) {
        await delay(stageTime);
        stages[i].progress = Math.min(p, 100);
        onStageUpdate([...stages]);
      }

      stages[i].status = 'completed';
      stages[i].progress = 100;
      onStageUpdate([...stages]);

      await delay(80);
    }

    let report: ForensicReport;

    if (file) {
      const isVideo = file.type.startsWith('video/');

      // For videos: skip ML server (images-only endpoint), go straight to client analyzer
      if (isVideo) {
        report = await analyzeImageFile(file);
      } else {
        // For images: try Python ML backend first, fallback to client-side
        try {
          const formData = new FormData();
          formData.append('file', file);
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 2500);

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
            } else {
              report = await analyzeImageFile(file);
            }
          } else {
            report = await analyzeImageFile(file);
          }
        } catch (_e) {
          // Fallback to advanced client-side forensic binary/EXIF/dimension analyzer
          report = await analyzeImageFile(file);
        }
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
