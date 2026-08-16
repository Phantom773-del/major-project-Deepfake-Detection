import React from 'react';
import { motion } from 'framer-motion';
import { Server, Zap } from 'lucide-react';
import { GlassCard } from '../common/GlassCard';
import { StatusBadge } from '../common/StatusBadge';
import type { SystemStatus as SystemStatusType } from '../../types';
import { formatDateTime } from '../../utils/formatters';

interface SystemStatusProps {
  data: SystemStatusType;
  loading?: boolean;
}

export const SystemStatus: React.FC<SystemStatusProps> = ({ data, loading }) => {
  if (loading) {
    return (
      <GlassCard>
        <div className="skeleton h-5 w-32 rounded mb-4" />
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => <div key={i} className="skeleton h-10 rounded" />)}
        </div>
      </GlassCard>
    );
  }

  return (
    <GlassCard>
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <Server className="w-4 h-4 text-cyan-400" />
          <h3 className="text-white font-semibold">System Status</h3>
        </div>
        <StatusBadge status={data.overallStatus} size="sm" />
      </div>

      <div className="space-y-3">
        {data.services.map((service, index) => (
          <motion.div
            key={service.name}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.06 }}
            className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900/40"
          >
            <div className="flex items-center gap-2.5">
              <div
                className="w-2 h-2 rounded-full"
                style={{
                  backgroundColor: service.status === 'operational' ? '#10b981' : service.status === 'degraded' ? '#f59e0b' : '#ef4444',
                  boxShadow: `0 0 6px ${service.status === 'operational' ? '#10b981' : service.status === 'degraded' ? '#f59e0b' : '#ef4444'}`,
                }}
              />
              <span className="text-slate-300 text-sm">{service.name}</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1 text-xs text-slate-500">
                <Zap className="w-3 h-3" />
                <span className="font-mono">{service.latency}ms</span>
              </div>
              <span className="text-xs font-mono text-slate-600">{service.uptime}%</span>
            </div>
          </motion.div>
        ))}
      </div>

      <p className="text-slate-700 text-xs font-mono mt-4">
        Last checked: {formatDateTime(data.lastChecked)}
      </p>
    </GlassCard>
  );
};
