import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { ReportHeader } from '../components/reports/ReportHeader';
import { MetadataTable } from '../components/reports/MetadataTable';
import { HeatmapViewer } from '../components/reports/HeatmapViewer';
import { ScoreGauge } from '../components/reports/ScoreGauge';
import { ShareModal } from '../components/reports/ShareModal';
import { GlassCard } from '../components/common/GlassCard';
import { reportService } from '../services/reportService';
import type { ForensicReport } from '../types';
import { exportReportToPDF } from '../utils/pdfExporter';
import { Shield, Brain, AlertTriangle } from 'lucide-react';

export const ReportPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<ForensicReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [shareModalOpen, setShareModalOpen] = useState(false);

  useEffect(() => {
    const fetchReport = async () => {
      try {
        const data = await reportService.getReport(id || 'RPT-2024-001847');
        setReport(data);
      } catch (err) {
        toast.error('Failed to load report data');
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, [id]);

  const handleDownload = () => {
    if (!report) return;
    try {
      toast.success('Generating and downloading Forensic PDF...');
      exportReportToPDF(report);
    } catch (err) {
      console.error(err);
      toast.error('Failed to generate PDF. Using print view instead.');
      window.print();
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleShare = () => {
    setShareModalOpen(true);
  };

  if (loading || !report) {
    return (
      <div className="p-10 max-w-5xl mx-auto space-y-6">
        <div className="skeleton h-32 rounded-2xl" />
        <div className="grid grid-cols-3 gap-6">
          <div className="skeleton h-48 rounded-2xl" />
          <div className="skeleton h-48 rounded-2xl" />
          <div className="skeleton h-48 rounded-2xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-10 space-y-8 max-w-6xl mx-auto">
      <ReportHeader
        report={report}
        onDownload={handleDownload}
        onPrint={handlePrint}
        onShare={handleShare}
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <GlassCard className="flex flex-col items-center justify-center border border-slate-800">
          <ScoreGauge score={report.authenticityScore} label="Authenticity Score" sublabel="LOW SCORE" color="#ef4444" />
        </GlassCard>
        <GlassCard className="flex flex-col items-center justify-center border border-slate-800">
          <ScoreGauge score={report.manipulationProbability} label="Manipulation Probability" sublabel="SYNTHETIC SIGS" color="#8b5cf6" />
        </GlassCard>
        <GlassCard className="flex flex-col items-center justify-center border border-slate-800">
          <ScoreGauge score={report.confidenceScore} label="Classifier Confidence" sublabel="HIGH PRECISION" color="#06b6d4" />
        </GlassCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard className="space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <Shield className="w-5 h-5 text-cyan-400" />
            <h3 className="text-lg font-bold text-white">Executive Forensic Summary</h3>
          </div>
          <p className="text-slate-300 text-sm leading-relaxed">
            Forensic analysis of <span className="text-cyan-400 font-mono">{report.fileName}</span> indicates a{' '}
            <strong className="text-purple-400">{report.manipulationProbability}% probability of AI generation</strong>. Multi-layer convolutional neural network classifiers identified spatial diffusion artifacts consistent with modern latent diffusion models.
          </p>
          <div className="p-4 bg-slate-900/60 rounded-xl border border-slate-800 space-y-2">
            <span className="text-xs text-slate-500 font-mono uppercase block">FREQUENCY DOMAIN ANOMALIES</span>
            <p className="text-xs text-slate-300 font-mono">
              Dominant Frequency: <span className="text-amber-400">{report.frequencyAnalysis.dominantFrequency}</span>
            </p>
            <p className="text-xs text-slate-300 font-mono">
              High-Frequency Anomaly Count: <span className="text-red-400">{report.frequencyAnalysis.anomalyCount} zones</span>
            </p>
          </div>
        </GlassCard>

        {report.aiAttribution && (
          <GlassCard className="space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <Brain className="w-5 h-5 text-purple-400" />
              <h3 className="text-lg font-bold text-white">AI Model Attribution</h3>
            </div>
            <div className="space-y-3">
              <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-xl flex items-center justify-between">
                <div>
                  <span className="text-xs text-purple-300 font-mono block">IDENTIFIED MODEL</span>
                  <span className="text-xl font-bold text-white">{report.aiAttribution.model}</span>
                </div>
                <div className="text-right">
                  <span className="text-xs text-purple-300 font-mono block">MATCH CONFIDENCE</span>
                  <span className="text-lg font-mono font-bold text-cyan-400">{report.aiAttribution.confidence}%</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800">
                  <span className="text-slate-500 block mb-1">GENERATION CLASS</span>
                  <span className="text-slate-200">{report.aiAttribution.generation}</span>
                </div>
                <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800">
                  <span className="text-slate-500 block mb-1">SYNTHESIS TECHNIQUE</span>
                  <span className="text-slate-200">{report.aiAttribution.technique}</span>
                </div>
              </div>
            </div>
          </GlassCard>
        )}
      </div>

      <HeatmapViewer imageUrl={report.explainableAI?.imageUrl} highRiskRegions={report.explainableAI?.highRiskRegions} />

      <MetadataTable metadata={report.metadata} />

      <GlassCard className="space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          <h3 className="text-lg font-bold text-white">Actionable Forensic Recommendations</h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {report.recommendations.map((rec, i) => (
            <div key={i} className="flex items-start gap-2.5 p-3 bg-slate-900/40 rounded-xl border border-slate-800/80 text-xs text-slate-300">
              <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-1.5 flex-shrink-0" />
              <span>{rec}</span>
            </div>
          ))}
        </div>
      </GlassCard>

      <ShareModal
        isOpen={shareModalOpen}
        onClose={() => setShareModalOpen(false)}
        report={report}
      />
    </div>
  );
};
