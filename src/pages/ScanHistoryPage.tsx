import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Clock, FileText, Shield, AlertTriangle, CheckCircle, Brain, ExternalLink } from 'lucide-react';
import { getStoredActivity } from '../services/dashboardStore';
import type { ActivityItem, Verdict, RiskLevel } from '../types';

const verdictConfig: Record<Verdict, { label: string; color: string; icon: React.ReactNode }> = {
  AUTHENTIC: { label: 'Authentic', color: 'text-emerald-400 bg-emerald-400/10 border-emerald-500/20', icon: <CheckCircle className="w-3.5 h-3.5" /> },
  AI_GENERATED: { label: 'AI Generated', color: 'text-purple-400 bg-purple-400/10 border-purple-500/20', icon: <Brain className="w-3.5 h-3.5" /> },
  MANIPULATED: { label: 'Manipulated', color: 'text-red-400 bg-red-400/10 border-red-500/20', icon: <AlertTriangle className="w-3.5 h-3.5" /> },
  SUSPICIOUS: { label: 'Suspicious', color: 'text-amber-400 bg-amber-400/10 border-amber-500/20', icon: <AlertTriangle className="w-3.5 h-3.5" /> },
  UNKNOWN: { label: 'Unknown', color: 'text-slate-400 bg-slate-400/10 border-slate-500/20', icon: <Shield className="w-3.5 h-3.5" /> },
};

const riskConfig: Record<RiskLevel, { label: string; color: string }> = {
  LOW: { label: 'LOW', color: 'text-emerald-400' },
  MEDIUM: { label: 'MED', color: 'text-amber-400' },
  HIGH: { label: 'HIGH', color: 'text-orange-400' },
  CRITICAL: { label: 'CRIT', color: 'text-red-400' },
};

const formatTime = (iso: string) => {
  if (iso === 'Just now') return iso;
  try {
    const d = new Date(iso);
    return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return iso;
  }
};

export const ScanHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const history: ActivityItem[] = getStoredActivity();

  return (
    <div className="p-6 md:p-10 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs mb-1">
            <Clock className="w-4 h-4" />
            <span>FORENSIC AUDIT TRAIL</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white">Scan History</h1>
          <p className="text-slate-400 text-sm mt-1">
            Complete record of all media forensic scans performed in this session
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-cyan-400">
            {history.length} total scans
          </div>
        </div>
      </div>

      {/* History Table / Cards */}
      {history.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-16 flex flex-col items-center justify-center text-center space-y-4"
        >
          <div className="w-16 h-16 rounded-2xl bg-slate-800/80 flex items-center justify-center">
            <Clock className="w-8 h-8 text-slate-600" />
          </div>
          <div>
            <h3 className="text-white font-semibold text-lg">No scans yet</h3>
            <p className="text-slate-400 text-sm mt-1">Upload a media file to run your first forensic analysis</p>
          </div>
          <button
            onClick={() => navigate('/upload')}
            className="btn-primary px-6 py-2.5 rounded-xl text-sm font-semibold"
          >
            Start First Scan
          </button>
        </motion.div>
      ) : (
        <div className="glass-card overflow-hidden">
          {/* Table header */}
          <div className="hidden md:grid grid-cols-[2fr_1fr_1fr_1fr_1fr_auto] gap-4 px-5 py-3 border-b border-slate-800 text-xs font-mono text-slate-500 uppercase tracking-wider">
            <span>File Name</span>
            <span>Type</span>
            <span>Verdict</span>
            <span>Risk</span>
            <span>Confidence</span>
            <span>Time</span>
          </div>

          <div className="divide-y divide-slate-800/60">
            {history.map((item, idx) => {
              const v = verdictConfig[item.verdict];
              const r = riskConfig[item.riskLevel];
              return (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.04 }}
                  className="flex flex-col md:grid md:grid-cols-[2fr_1fr_1fr_1fr_1fr_auto] gap-3 md:gap-4 px-5 py-4 hover:bg-slate-800/30 transition-colors group"
                >
                  {/* File Name */}
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center flex-shrink-0">
                      <FileText className="w-4 h-4 text-slate-500" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-white truncate">{item.fileName}</p>
                      <p className="text-xs text-slate-500 font-mono">{item.id}</p>
                    </div>
                  </div>

                  {/* Type */}
                  <div className="flex items-center">
                    <span className="text-xs text-slate-400 capitalize font-mono">{item.mediaType}</span>
                  </div>

                  {/* Verdict */}
                  <div className="flex items-center">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold border ${v.color}`}>
                      {v.icon}
                      {v.label}
                    </span>
                  </div>

                  {/* Risk Level */}
                  <div className="flex items-center">
                    <span className={`text-xs font-bold font-mono ${r.color}`}>{r.label}</span>
                  </div>

                  {/* Confidence */}
                  <div className="flex items-center">
                    <div className="space-y-1 w-full">
                      <span className="text-sm font-bold text-white font-mono">{item.confidenceScore.toFixed(1)}%</span>
                      <div className="h-1 bg-slate-800 rounded-full w-24 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-blue-500"
                          style={{ width: `${item.confidenceScore}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Time + Action */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500 font-mono whitespace-nowrap">{formatTime(item.timestamp)}</span>
                    {item.reportId && (
                      <button
                        onClick={() => navigate(`/report/${item.reportId}`)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg hover:bg-cyan-500/10 text-cyan-400"
                        title="View Report"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
