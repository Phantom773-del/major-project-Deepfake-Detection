import React, { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { get15DayTrendData } from '../../services/analyticsStore';
import { GlassCard } from '../common/GlassCard';

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-card p-3 border border-slate-700/50">
      <p className="text-cyan-400 text-xs font-mono mb-2">{label}</p>
      {payload.map((entry: any) => (
        <div key={entry.name} className="flex items-center gap-2 text-xs mb-1">
          <div className="w-2 h-2 rounded-full" style={{ background: entry.color }} />
          <span className="text-slate-400">{entry.name}:</span>
          <span className="text-white font-semibold">{entry.value.toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
};

export const DailyActivityChart: React.FC = () => {
  const data = useMemo(() => get15DayTrendData(), []);

  return (
    <GlassCard>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-white font-semibold">15-Day Scan History</h3>
          <p className="text-slate-500 text-xs mt-0.5">Daily scan distribution over past 15 days</p>
        </div>
        <div className="text-xs font-mono px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-cyan-400">
          15-DAY TIMELINE
        </div>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: -20 }} barGap={2}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.06)" vertical={false} />
          <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ paddingTop: 16, fontSize: 12 }} />
          <Bar dataKey="authentic" name="Authentic" fill="#10b981" fillOpacity={0.85} radius={[2, 2, 0, 0]} />
          <Bar dataKey="aiGenerated" name="AI Generated" fill="#8b5cf6" fillOpacity={0.85} radius={[2, 2, 0, 0]} />
          <Bar dataKey="suspicious" name="Suspicious" fill="#f59e0b" fillOpacity={0.85} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </GlassCard>
  );
};
