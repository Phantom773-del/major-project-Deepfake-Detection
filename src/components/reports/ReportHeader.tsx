import React from 'react';
import { Download, Printer, Share2, Shield, Calendar, Clock } from 'lucide-react';
import { VerdictBadge } from './VerdictBadge';
import type { ForensicReport } from '../../types';
import { formatDateTime } from '../../utils/formatters';

interface ReportHeaderProps {
  report: ForensicReport;
  onDownload: () => void;
  onPrint: () => void;
  onShare: () => void;
}

export const ReportHeader: React.FC<ReportHeaderProps> = ({
  report,
  onDownload,
  onPrint,
  onShare,
}) => {
  return (
    <div className="glass-card p-6 md:p-8 space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs tracking-wider mb-2">
            <Shield className="w-4 h-4" />
            <span>FORENSIC INTELLIGENCE REPORT</span>
            <span>•</span>
            <span>{report.id}</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white">
            Media Analysis: {report.fileName}
          </h1>
          <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-400 mt-2">
            <span className="flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-slate-500" />
              {formatDateTime(report.createdAt)}
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-slate-500" />
              Processing: {report.processingTime}s
            </span>
            <span className="text-slate-500">Version: {report.analysisVersion}</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={onDownload}
            className="btn-primary text-xs px-4 py-2.5 rounded-lg flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            <span>Download PDF</span>
          </button>
          <button
            onClick={onPrint}
            className="btn-secondary text-xs px-4 py-2.5 rounded-lg flex items-center gap-2"
          >
            <Printer className="w-4 h-4" />
            <span>Print</span>
          </button>
          <button
            onClick={onShare}
            className="btn-secondary text-xs px-4 py-2.5 rounded-lg flex items-center gap-2"
          >
            <Share2 className="w-4 h-4" />
            <span>Share</span>
          </button>
        </div>
      </div>

      {/* Verdict Row */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
        <div>
          <span className="text-xs text-slate-500 font-mono block mb-1">FINAL VERDICT</span>
          <VerdictBadge verdict={report.verdict} riskLevel={report.riskLevel} />
        </div>

        <div className="flex items-center gap-6">
          <div className="text-right">
            <span className="text-xs text-slate-500 font-mono block">CONFIDENCE</span>
            <span className="text-xl font-bold text-cyan-400">{report.confidenceScore}%</span>
          </div>
          <div className="w-px h-8 bg-slate-800" />
          <div className="text-right">
            <span className="text-xs text-slate-500 font-mono block">MANIPULATION PROB.</span>
            <span className="text-xl font-bold text-red-400">{report.manipulationProbability}%</span>
          </div>
        </div>
      </div>
    </div>
  );
};
