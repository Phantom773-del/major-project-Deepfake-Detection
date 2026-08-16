import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { GlassCard } from '../common/GlassCard';
import { AnimatedCounter } from '../common/AnimatedCounter';

interface StatCardProps {
  title: string;
  value: number;
  suffix?: string;
  prefix?: string;
  decimals?: number;
  icon: React.ReactNode;
  trend?: number;
  trendLabel?: string;
  color: string;
  delay?: number;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  suffix = '',
  prefix = '',
  decimals = 0,
  icon,
  trend,
  trendLabel,
  color,
  delay = 0,
}) => {
  const trendPositive = trend && trend > 0;
  const trendNegative = trend && trend < 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.5 }}
    >
      <GlassCard hover>
        <div className="flex items-start justify-between mb-4">
          <div
            className="w-11 h-11 rounded-xl flex items-center justify-center"
            style={{ background: `${color}18`, border: `1px solid ${color}30` }}
          >
            <div style={{ color }}>{icon}</div>
          </div>
          {trend !== undefined && (
            <div className={`flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-full
              ${trendPositive ? 'text-green-400 bg-green-400/10' : trendNegative ? 'text-red-400 bg-red-400/10' : 'text-slate-400 bg-slate-400/10'}`}>
              {trendPositive ? <TrendingUp className="w-3 h-3" /> : trendNegative ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
              {Math.abs(trend || 0)}%
            </div>
          )}
        </div>

        <div className="mb-1">
          <AnimatedCounter
            target={value}
            suffix={suffix}
            prefix={prefix}
            decimals={decimals}
            className="text-3xl font-bold text-white"
          />
        </div>
        <p className="text-slate-500 text-sm">{title}</p>
        {trendLabel && (
          <p className="text-slate-600 text-xs mt-1">{trendLabel}</p>
        )}

        {/* Bottom accent bar */}
        <div className="mt-4 h-0.5 rounded-full overflow-hidden" style={{ background: 'rgba(148,163,184,0.08)' }}>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: '70%' }}
            transition={{ delay: delay + 0.5, duration: 0.8, ease: 'easeOut' }}
            className="h-full rounded-full"
            style={{ background: `linear-gradient(90deg, ${color}, transparent)` }}
          />
        </div>
      </GlassCard>
    </motion.div>
  );
};
