import React from 'react';
import { GlassCard } from '../common/GlassCard';
import type { MetadataInfo } from '../../types';
import { FileText, Camera, Tag } from 'lucide-react';

interface MetadataTableProps {
  metadata: MetadataInfo;
}

export const MetadataTable: React.FC<MetadataTableProps> = ({ metadata }) => {
  return (
    <GlassCard className="space-y-6">
      <div className="flex items-center gap-2 border-b border-slate-800 pb-4">
        <FileText className="w-5 h-5 text-cyan-400" />
        <h3 className="text-lg font-bold text-white">Metadata & File Intelligence</h3>
      </div>

      {/* File General Info Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800">
          <span className="text-xs text-slate-500 font-mono block mb-1">MIME TYPE</span>
          <span className="text-sm font-semibold text-white truncate block">{metadata.mimeType}</span>
        </div>
        <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800">
          <span className="text-xs text-slate-500 font-mono block mb-1">FILE SIZE</span>
          <span className="text-sm font-semibold text-white truncate block">{metadata.fileSize}</span>
        </div>
        <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800">
          <span className="text-xs text-slate-500 font-mono block mb-1">DIMENSIONS</span>
          <span className="text-sm font-semibold text-white truncate block">{metadata.dimensions || 'N/A'}</span>
        </div>
        <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800">
          <span className="text-xs text-slate-500 font-mono block mb-1">SOFTWARE</span>
          <span className="text-sm font-semibold text-cyan-400 truncate block">{metadata.software || 'Unknown'}</span>
        </div>
      </div>

      {/* EXIF Data Table */}
      {metadata.exifData && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400 uppercase tracking-wider">
            <Camera className="w-4 h-4 text-slate-500" />
            <span>Extracted EXIF Headers</span>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Header Tag</th>
                  <th>Extracted Value</th>
                  <th>Forensic Status</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(metadata.exifData).map(([key, val]) => (
                  <tr key={key}>
                    <td className="font-mono text-cyan-400 text-xs">{key}</td>
                    <td className="font-mono text-slate-300 text-xs">{val}</td>
                    <td>
                      {val.includes('AI') || val.includes('N/A') ? (
                        <span className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          <Tag className="w-3 h-3" /> SYNTHETIC TAG
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          VALID HEADER
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </GlassCard>
  );
};
