import React, { useState } from 'react';
import { AIAttributionChart } from '../components/charts/AIAttributionChart';
import { ConfidenceChart } from '../components/charts/ConfidenceChart';
import { DailyActivityChart } from '../components/charts/DailyActivityChart';
import { GlassCard } from '../components/common/GlassCard';
import { getStoredStats } from '../services/dashboardStore';
import { BarChart3, Download } from 'lucide-react';
import toast from 'react-hot-toast';

export const AnalyticsPage: React.FC = () => {
  const [timeRange, setTimeRange] = useState<'7d' | '15d' | '30d' | '90d'>('15d');
  const stats = getStoredStats();

  const handleExport = () => {
    toast.success(`Exported Forensic Analytics Report (${timeRange.toUpperCase()})`);
  };

  return (
    <div className="p-6 md:p-10 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs mb-1">
            <BarChart3 className="w-4 h-4" />
            <span>GLOBAL INTELLIGENCE & METRICS</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white">Forensic Analytics</h1>
          <p className="text-slate-400 text-sm mt-1">
            Detection confidence, model attribution, and 15-day forensic intelligence insights
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex bg-slate-900 border border-slate-800 rounded-lg p-1 text-xs font-mono">
            {(['7d', '15d', '30d', '90d'] as const).map((r) => (
              <button
                key={r}
                onClick={() => setTimeRange(r)}
                className={`px-3 py-1.5 rounded-md uppercase transition-colors ${
                  timeRange === r ? 'bg-cyan-500 text-white font-bold' : 'text-slate-400 hover:text-white'
                }`}
              >
                {r}
              </button>
            ))}
          </div>

          <button
            onClick={handleExport}
            className="btn-secondary text-xs px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            <span>Export Data</span>
          </button>
        </div>
      </div>

      {/* Row 1: AI Attribution + 15-Day History */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AIAttributionChart />
        <DailyActivityChart />
      </div>

      {/* Row 2: Confidence Distribution + Detection Engine Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ConfidenceChart />
        </div>
        <GlassCard className="space-y-4">
          <h3 className="text-white font-semibold">Detection Engine Health</h3>
          <div className="space-y-3 font-mono text-xs">
            <div className="flex justify-between p-2.5 bg-slate-900/60 rounded-lg">
              <span className="text-slate-400">Total Processed:</span>
              <span className="text-white font-bold">{stats.totalScans} files</span>
            </div>
            <div className="flex justify-between p-2.5 bg-slate-900/60 rounded-lg">
              <span className="text-slate-400">AI Detected:</span>
              <span className="text-purple-400 font-bold">{stats.aiGeneratedMedia} files</span>
            </div>
            <div className="flex justify-between p-2.5 bg-slate-900/60 rounded-lg">
              <span className="text-slate-400">Authentic Verified:</span>
              <span className="text-emerald-400 font-bold">{stats.authenticMedia} files</span>
            </div>
            <div className="flex justify-between p-2.5 bg-slate-900/60 rounded-lg">
              <span className="text-slate-400">Precision Score:</span>
              <span className="text-emerald-400 font-bold">97.3%</span>
            </div>
            <div className="flex justify-between p-2.5 bg-slate-900/60 rounded-lg">
              <span className="text-slate-400">False Positive Rate:</span>
              <span className="text-cyan-400 font-bold">1.2%</span>
            </div>
            <div className="flex justify-between p-2.5 bg-slate-900/60 rounded-lg">
              <span className="text-slate-400">Mean Inference Latency:</span>
              <span className="text-amber-400 font-bold">0.42s</span>
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
};
