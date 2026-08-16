import React from 'react';
import type { Verdict, RiskLevel } from '../../types';

interface StatusBadgeProps {
  verdict?: Verdict;
  risk?: RiskLevel;
  status?: 'operational' | 'degraded' | 'down' | 'pending' | 'active' | 'completed' | 'error';
  size?: 'sm' | 'md' | 'lg';
}

const verdictConfig: Record<Verdict, { label: string; color: string; bg: string; border: string }> = {
  AUTHENTIC: { label: 'REAL', color: '#10b981', bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.35)' },
  MANIPULATED: { label: 'FAKE', color: '#ef4444', bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.35)' },
  AI_GENERATED: { label: 'FAKE', color: '#ef4444', bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.35)' },
  SUSPICIOUS: { label: 'FAKE', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.35)' },
  UNKNOWN: { label: 'UNKNOWN', color: '#64748b', bg: 'rgba(100,116,139,0.12)', border: 'rgba(100,116,139,0.35)' },
};

const riskConfig: Record<RiskLevel, { label: string; color: string; bg: string; border: string }> = {
  LOW: { label: 'LOW RISK', color: '#10b981', bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.35)' },
  MEDIUM: { label: 'MEDIUM RISK', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.35)' },
  HIGH: { label: 'HIGH RISK', color: '#ef4444', bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.35)' },
  CRITICAL: { label: 'CRITICAL', color: '#dc2626', bg: 'rgba(220,38,38,0.15)', border: 'rgba(220,38,38,0.5)' },
};

const statusConfig = {
  operational: { label: 'OPERATIONAL', color: '#10b981', bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.35)' },
  degraded: { label: 'DEGRADED', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.35)' },
  down: { label: 'DOWN', color: '#ef4444', bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.35)' },
  pending: { label: 'PENDING', color: '#64748b', bg: 'rgba(100,116,139,0.12)', border: 'rgba(100,116,139,0.35)' },
  active: { label: 'PROCESSING', color: '#06b6d4', bg: 'rgba(6,182,212,0.12)', border: 'rgba(6,182,212,0.35)' },
  completed: { label: 'COMPLETED', color: '#10b981', bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.35)' },
  error: { label: 'ERROR', color: '#ef4444', bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.35)' },
};

const sizeMap = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-3 py-1 text-xs',
  lg: 'px-4 py-1.5 text-sm',
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  verdict,
  risk,
  status,
  size = 'md',
}) => {
  let config = { label: 'UNKNOWN', color: '#64748b', bg: 'rgba(100,116,139,0.12)', border: 'rgba(100,116,139,0.35)' };

  if (verdict) config = verdictConfig[verdict];
  else if (risk) config = riskConfig[risk];
  else if (status) config = statusConfig[status];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold tracking-wider ${sizeMap[size]}`}
      style={{ color: config.color, background: config.bg, border: `1px solid ${config.border}` }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: config.color, boxShadow: `0 0 4px ${config.color}` }}
      />
      {config.label}
    </span>
  );
};
