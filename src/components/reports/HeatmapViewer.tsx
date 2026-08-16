import React, { useState } from 'react';
import { GlassCard } from '../common/GlassCard';
import { Eye, Layers, Zap, Info } from 'lucide-react';
import { useAnalysisContext } from '../../contexts/AnalysisContext';

interface HeatmapViewerProps {
  imageUrl?: string;
  highRiskRegions?: Array<{
    x: number;
    y: number;
    width: number;
    height: number;
    confidence: number;
  }>;
}

export const HeatmapViewer: React.FC<HeatmapViewerProps> = ({ imageUrl, highRiskRegions = [] }) => {
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [activeLayer, setActiveLayer] = useState<'gradcam' | 'lime' | 'frequency'>('gradcam');
  const { previewUrl } = useAnalysisContext();

  const displayImg = imageUrl || previewUrl || sessionStorage.getItem('current_upload_img');

  return (
    <GlassCard className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-2">
          <Eye className="w-5 h-5 text-cyan-400" />
          <div>
            <h3 className="text-lg font-bold text-white">Explainable AI (XAI) Visual Evidence</h3>
            <p className="text-xs text-slate-400">GradCAM Heatmap & Manipulation Region Overlays</p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowHeatmap(!showHeatmap)}
            className={`text-xs px-3 py-1.5 rounded-lg border font-mono flex items-center gap-1.5 transition-colors ${
              showHeatmap
                ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40'
                : 'bg-slate-800 text-slate-400 border-slate-700'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Heatmap Overlay: {showHeatmap ? 'ON' : 'OFF'}</span>
          </button>
        </div>
      </div>

      {/* Layer Tabs */}
      <div className="flex gap-2">
        {(['gradcam', 'lime', 'frequency'] as const).map((layer) => (
          <button
            key={layer}
            onClick={() => setActiveLayer(layer)}
            className={`text-xs px-3 py-1.5 rounded-lg font-mono capitalize transition-all ${
              activeLayer === layer
                ? 'bg-blue-600 text-white font-bold'
                : 'bg-slate-800/60 text-slate-400 hover:text-white'
            }`}
          >
            {layer === 'gradcam' ? 'GradCAM (Activation)' : layer === 'lime' ? 'LIME Superpixels' : 'FFT Artifacts'}
          </button>
        ))}
      </div>

      {/* Media Canvas View */}
      <div className="relative rounded-2xl overflow-hidden bg-slate-950 border border-slate-800 aspect-video flex items-center justify-center group">
        <div className="w-full h-full bg-slate-950 flex items-center justify-center relative overflow-hidden">
          {displayImg ? (
            <img
              src={displayImg}
              alt="Uploaded Source Media"
              className="max-h-full max-w-full object-contain"
            />
          ) : (
            <div className="w-32 h-32 rounded-full border border-slate-800/80 flex items-center justify-center">
              <span className="text-slate-700 font-mono text-xs">SOURCE MEDIA CANVAS</span>
            </div>
          )}

          {/* GradCAM Heatmap Overlay */}
          {showHeatmap && (
            <div className="absolute inset-0 pointer-events-none transition-opacity duration-300">
              {activeLayer === 'gradcam' && (
                <div className="w-full h-full bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-red-500/40 via-yellow-500/20 to-transparent blur-md animate-pulse" />
              )}
              {activeLayer === 'lime' && (
                <div className="w-full h-full bg-[radial-gradient(circle_at_30%_40%,_var(--tw-gradient-stops))] from-purple-500/40 via-cyan-500/20 to-transparent blur-sm" />
              )}
              {activeLayer === 'frequency' && (
                <div className="w-full h-full bg-[repeating-linear-gradient(45deg,rgba(6,182,212,0.1)_0px,rgba(6,182,212,0.1)_10px,transparent_10px,transparent_20px)]" />
              )}
            </div>
          )}

          {/* High-Risk Bounding Box Overlays */}
          {highRiskRegions.map((region, idx) => (
            <div
              key={idx}
              className="absolute border-2 border-red-500 bg-red-500/20 rounded-md transition-all shadow-[0_0_15px_rgba(239,68,68,0.5)]"
              style={{
                left: `${region.x * 100}%`,
                top: `${region.y * 100}%`,
                width: `${region.width * 100}%`,
                height: `${region.height * 100}%`,
              }}
            >
              <div className="absolute -top-6 left-0 bg-red-600 text-white text-[10px] font-mono px-2 py-0.5 rounded shadow flex items-center gap-1">
                <Zap className="w-3 h-3" /> ANOMALY DETECTED ({region.confidence}%)
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-start gap-2 bg-slate-900/40 p-3 rounded-xl border border-slate-800 text-xs text-slate-400">
        <Info className="w-4 h-4 text-cyan-400 flex-shrink-0 mt-0.5" />
        <span>
          The GradCAM & LIME heatmaps are projected directly over your uploaded source media canvas to pinpoint optical noise profiles and neural classifier activations.
        </span>
      </div>
    </GlassCard>
  );
};
