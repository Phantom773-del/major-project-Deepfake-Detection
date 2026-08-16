import React, { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { get15DayConfidenceDist } from '../../services/analyticsStore';
import { GlassCard } from '../common/GlassCard';

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-card p-3 border border-slate-700/50">
      <p className="text-cyan-400 text-xs font-mono mb-1">{label}</p>
      <p className="text-white font-semibold">{payload[0].value.toLocaleString()} scans</p>
    </div>
  );
};

export const ConfidenceChart: React.FC = () => {
  const data = useMemo(() => get15DayConfidenceDist(), []);

  return (
    <GlassCard>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-white font-semibold">Confidence Distribution</h3>
          <p className="text-slate-500 text-xs mt-0.5">Score frequency across past 15 days scans</p>
        </div>
        <div className="text-xs font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-cyan-400">
          15D METRICS
        </div>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 0, right: 5, bottom: 0, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.06)" vertical={false} />
          <XAxis dataKey="range" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="count" fill="url(#confGrad)" radius={[4, 4, 0, 0]} />
          <defs>
            <linearGradient id="confGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.9} />
              <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.5} />
            </linearGradient>
          </defs>
        </BarChart>
      </ResponsiveContainer>
    </GlassCard>
  );
};
