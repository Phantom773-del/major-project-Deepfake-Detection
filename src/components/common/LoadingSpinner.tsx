import React from 'react';
import { motion } from 'framer-motion';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

const sizeMap = { sm: 16, md: 24, lg: 40, xl: 64 };

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = 'md', className = '' }) => {
  const s = sizeMap[size];
  return (
    <div className={`flex items-center justify-center ${className}`}>
      <svg width={s} height={s} viewBox="0 0 50 50">
        <motion.circle
          cx="25" cy="25" r="20"
          fill="none"
          stroke="url(#spinnerGrad)"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray="80 40"
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        />
        <defs>
          <linearGradient id="spinnerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#06b6d4" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
};

export const PageLoader: React.FC = () => (
  <div className="flex flex-col items-center justify-center min-h-screen bg-forensic gap-6">
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col items-center gap-6"
    >
      <div className="relative">
        <LoadingSpinner size="xl" />
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-3 h-3 rounded-full bg-cyan-400 animate-pulse" />
        </div>
      </div>
      <div className="text-center">
        <p className="text-cyan-400 font-mono text-sm tracking-widest animate-pulse">
          PHANTOM PHOENIX
        </p>
        <p className="text-slate-500 text-xs mt-1 font-mono">INITIALIZING FORENSIC ENGINE...</p>
      </div>
    </motion.div>
  </div>
);

export const SkeletonLoader: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`skeleton h-4 rounded ${className}`} />
);
