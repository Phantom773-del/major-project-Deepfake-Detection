import React from 'react';
import type { Verdict, RiskLevel } from '../../types';

interface VerdictBadgeProps {
  verdict: Verdict;
  riskLevel: RiskLevel;
}

export const VerdictBadge: React.FC<VerdictBadgeProps> = ({ verdict }) => {
  const isReal = verdict === 'AUTHENTIC';
  const label = isReal ? 'REAL' : 'FAKE';
  const color = isReal ? '#10b981' : '#ef4444';
  const bg = isReal ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)';
  const border = isReal ? 'rgba(16,185,129,0.4)' : 'rgba(239,68,68,0.4)';

  return (
    <span
      className="inline-flex items-center gap-2 px-5 py-2 rounded-full font-extrabold text-base tracking-widest"
      style={{ color, background: bg, border: `1px solid ${border}` }}
    >
      <span
        className="w-2.5 h-2.5 rounded-full"
        style={{ backgroundColor: color, boxShadow: `0 0 8px ${color}` }}
      />
      {label}
    </span>
  );
};

