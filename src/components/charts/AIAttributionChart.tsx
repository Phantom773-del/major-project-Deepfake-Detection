import React, { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import { get15DayAIAttribution } from '../../services/analyticsStore';
import { GlassCard } from '../common/GlassCard';

const COLORS = ['#3b82f6', '#06b6d4', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444'];

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="glass-card p-3 border border-slate-700/50">
      <p className="text-white font-semibold text-sm">{d.payload.model}</p>
      <p className="text-slate-400 text-xs">{d.value.toLocaleString()} detections ({d.payload.percentage}%)</p>
    </div>
  );
};

export const AIAttributionChart: React.FC = () => {
  const data = useMemo(() => get15DayAIAttribution(), []);

  return (
    <GlassCard>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-white font-semibold">AI Model Attribution</h3>
          <p className="text-slate-500 text-xs mt-0.5">Identified generative sources over past 15 days</p>
        </div>
        <div className="text-xs font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-purple-400">
          15D ANALYSIS
        </div>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 10, bottom: 0, left: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.06)" horizontal={false} />
          <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
          <YAxis type="category" dataKey="model" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} width={58} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="count" radius={[0, 4, 4, 0]}>
            {data.map((_, index) => (
              <Cell key={index} fill={COLORS[index % COLORS.length]} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </GlassCard>
  );
};
