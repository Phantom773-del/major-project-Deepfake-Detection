import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Settings, Trash2, RotateCcw, Download, Info, Shield, Database, Cpu, Eye } from 'lucide-react';
import toast from 'react-hot-toast';
import { clearStoredData } from '../services/dashboardStore';
import { reportService } from '../services/reportService';

interface ToggleProps {
  value: boolean;
  onChange: (v: boolean) => void;
}
const Toggle: React.FC<ToggleProps> = ({ value, onChange }) => (
  <button
    onClick={() => onChange(!value)}
    className={`relative w-10 h-5 rounded-full transition-colors duration-200 ${value ? 'bg-cyan-500' : 'bg-slate-700'}`}
  >
    <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200 ${value ? 'translate-x-5' : 'translate-x-0.5'}`} />
  </button>
);

const SectionCard: React.FC<{ title: string; icon: React.ReactNode; children: React.ReactNode }> = ({ title, icon, children }) => (
  <motion.div
    initial={{ opacity: 0, y: 12 }}
    animate={{ opacity: 1, y: 0 }}
    className="glass-card p-6 space-y-5"
  >
    <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
      <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
        {icon}
      </div>
      <h2 className="text-white font-semibold">{title}</h2>
    </div>
    {children}
  </motion.div>
);

export const SettingsPage: React.FC = () => {
  const [autoAnalyze, setAutoAnalyze] = useState(false);
  const [heatmapOverlay, setHeatmapOverlay] = useState(true);
  const [highConfidenceOnly, setHighConfidenceOnly] = useState(false);
  const [exportPDF, setExportPDF] = useState(true);
  const [notifications, setNotifications] = useState(true);
  const [theme, setTheme] = useState<'dark' | 'darker'>('dark');

  const handleClearHistory = () => {
    clearStoredData();
    reportService.clearAll();
    toast.success('All scan history and reports cleared');
  };

  const handleExportLogs = () => {
    const logs = localStorage.getItem('phantom_recent_activity') || '[]';
    const blob = new Blob([logs], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `phantom_scan_logs_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Scan logs exported');
  };

  const handleResetDefaults = () => {
    setAutoAnalyze(false);
    setHeatmapOverlay(true);
    setHighConfidenceOnly(false);
    setExportPDF(true);
    setNotifications(true);
    setTheme('dark');
    toast.success('Settings reset to defaults');
  };

  return (
    <div className="p-6 md:p-10 space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs mb-1">
          <Settings className="w-4 h-4" />
          <span>SYSTEM CONFIGURATION</span>
        </div>
        <h1 className="text-2xl md:text-3xl font-extrabold text-white">Settings</h1>
        <p className="text-slate-400 text-sm mt-1">Customize the PHANTOM PHOENIX forensic platform behavior</p>
      </div>

      {/* Analysis Settings */}
      <SectionCard title="Analysis Configuration" icon={<Cpu className="w-4 h-4" />}>
        <div className="space-y-4">
          {[
            {
              label: 'Auto-analyze on upload',
              desc: 'Automatically start analysis as soon as a file is uploaded',
              value: autoAnalyze,
              onChange: setAutoAnalyze,
            },
            {
              label: 'High confidence mode only',
              desc: 'Only flag media with confidence score above 90%',
              value: highConfidenceOnly,
              onChange: setHighConfidenceOnly,
            },
          ].map(({ label, desc, value, onChange }) => (
            <div key={label} className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-white">{label}</p>
                <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
              </div>
              <Toggle value={value} onChange={onChange} />
            </div>
          ))}

          <div className="pt-2">
            <label className="block text-sm font-medium text-white mb-2">Detection Sensitivity</label>
            <div className="flex gap-2">
              {(['Low', 'Medium', 'High', 'Max'] as const).map(level => (
                <button
                  key={level}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                    level === 'High'
                      ? 'bg-cyan-500/15 border-cyan-500/40 text-cyan-400'
                      : 'border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-300'
                  }`}
                >
                  {level}
                </button>
              ))}
            </div>
          </div>
        </div>
      </SectionCard>

      {/* Display Settings */}
      <SectionCard title="Display & Reports" icon={<Eye className="w-4 h-4" />}>
        <div className="space-y-4">
          {[
            {
              label: 'Show heatmap overlay by default',
              desc: 'Automatically show GradCAM heatmap on report page',
              value: heatmapOverlay,
              onChange: setHeatmapOverlay,
            },
            {
              label: 'Auto-generate PDF on completion',
              desc: 'Download PDF report automatically after analysis',
              value: exportPDF,
              onChange: setExportPDF,
            },
            {
              label: 'Enable desktop notifications',
              desc: 'Get notified when forensic analysis completes',
              value: notifications,
              onChange: setNotifications,
            },
          ].map(({ label, desc, value, onChange }) => (
            <div key={label} className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-white">{label}</p>
                <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
              </div>
              <Toggle value={value} onChange={onChange} />
            </div>
          ))}

          <div className="pt-2">
            <label className="block text-sm font-medium text-white mb-2">UI Theme</label>
            <div className="flex gap-2">
              {(['dark', 'darker'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setTheme(t)}
                  className={`px-4 py-1.5 rounded-lg text-xs font-semibold border capitalize transition-all ${
                    theme === t
                      ? 'bg-cyan-500/15 border-cyan-500/40 text-cyan-400'
                      : 'border-slate-700 text-slate-400 hover:border-slate-600'
                  }`}
                >
                  {t === 'dark' ? 'Cyber Dark' : 'Deep Black'}
                </button>
              ))}
            </div>
          </div>
        </div>
      </SectionCard>

      {/* Data Management */}
      <SectionCard title="Data Management" icon={<Database className="w-4 h-4" />}>
        <div className="space-y-3">
          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 flex items-start gap-3">
            <Info className="w-4 h-4 text-cyan-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-slate-400 leading-relaxed">
              All scan data is stored locally in your browser. No data is sent to external servers.
              Reports are retained until you clear them manually.
            </p>
          </div>

          <div className="flex flex-wrap gap-3 pt-2">
            <button
              onClick={handleExportLogs}
              className="btn-secondary flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm"
            >
              <Download className="w-4 h-4" />
              Export Scan Logs
            </button>
            <button
              onClick={handleResetDefaults}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm border border-slate-700 text-slate-300 hover:border-slate-600 hover:bg-slate-800/50 transition-all"
            >
              <RotateCcw className="w-4 h-4" />
              Reset Defaults
            </button>
            <button
              onClick={handleClearHistory}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-all"
            >
              <Trash2 className="w-4 h-4" />
              Clear All History
            </button>
          </div>
        </div>
      </SectionCard>

      {/* About */}
      <SectionCard title="About PHANTOM PHOENIX" icon={<Shield className="w-4 h-4" />}>
        <div className="space-y-3 font-mono text-xs">
          {[
            ['Platform Version', 'v2.1.0'],
            ['Detection Engine', 'PHANTOM-PHOENIX-AI v2.1'],
            ['Model Architecture', 'Multi-Model Ensemble (CNN + Transformer)'],
            ['Benchmark Accuracy', '97.3% on FaceForensics++'],
            ['License', 'Enterprise (Academic Research)'],
          ].map(([key, val]) => (
            <div key={key} className="flex justify-between py-2 border-b border-slate-800/60 last:border-0">
              <span className="text-slate-500">{key}</span>
              <span className="text-slate-300">{val}</span>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  );
};
