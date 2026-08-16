import React from 'react';
import { motion } from 'framer-motion';
import { GlassCard } from '../common/GlassCard';

interface UploadProgressProps {
  progress: number;
  fileName: string;
}

export const UploadProgress: React.FC<UploadProgressProps> = ({ progress, fileName }) => {
  return (
    <GlassCard glow className="py-8">
      <div className="max-w-md mx-auto space-y-6 text-center">
        <div className="space-y-2">
          <h3 className="text-xl font-bold text-white">Uploading Media File</h3>
          <p className="text-slate-400 text-sm truncate font-mono">{fileName}</p>
        </div>

        <div className="relative pt-2">
          <div className="flex justify-between text-xs font-mono text-cyan-400 mb-2">
            <span>UPLOADING...</span>
            <span>{progress}%</span>
          </div>

          <div className="h-3 bg-slate-900 rounded-full overflow-hidden border border-slate-800 p-0.5">
            <motion.div
              className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full shadow-[0_0_12px_#06b6d4]"
              initial={{ width: '0%' }}
              animate={{ width: `${progress}%` }}
              transition={{ ease: 'easeOut' }}
            />
          </div>
        </div>
      </div>
    </GlassCard>
  );
};
