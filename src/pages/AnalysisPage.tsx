import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAnalysisContext } from '../contexts/AnalysisContext';
import { analysisService } from '../services/analysisService';
import { GlassCard } from '../components/common/GlassCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { Shield, CheckCircle2, Loader2 } from 'lucide-react';

export const AnalysisPage: React.FC = () => {
  const navigate = useNavigate();
  const { stages, setStages, jobId, fileName, selectedFile, setReportId, setStatus } = useAnalysisContext();

  useEffect(() => {
    let isMounted = true;

    const executeAnalysis = async () => {
      const currentJobId = jobId || 'JOB-SIMULATED-001';

      try {
        const reportId = await analysisService.runAnalysis(currentJobId, selectedFile, (updatedStages) => {
          if (isMounted) {
            setStages(updatedStages);
          }
        });


        if (isMounted) {
          setReportId(reportId);
          setStatus('completed');
          setTimeout(() => {
            if (isMounted) navigate(`/report/${reportId}`);
          }, 1200);
        }
      } catch (err) {
        if (isMounted) setStatus('error');
      }
    };

    executeAnalysis();

    return () => {
      isMounted = false;
    };
  }, []);

  const completedCount = stages.filter((s) => s.status === 'completed').length;
  const overallProgress = Math.round((completedCount / stages.length) * 100);

  return (
    <div className="p-6 md:p-10 space-y-8 max-w-4xl mx-auto">
      <div>
        <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs mb-1">
          <Shield className="w-4 h-4" />
          <span>LIVE FORENSIC PIPELINE</span>
        </div>
        <h1 className="text-2xl md:text-3xl font-extrabold text-white">Analyzing Media Authenticity</h1>
        <p className="text-slate-400 text-sm mt-1 font-mono">
          File: <span className="text-cyan-400">{fileName || 'suspect_media_001.jpg'}</span>
        </p>
      </div>

      <GlassCard glow className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono text-slate-400 uppercase tracking-widest">
            OVERALL PIPELINE EXECUTION
          </span>
          <span className="text-lg font-bold font-mono text-cyan-400">{overallProgress}%</span>
        </div>

        <div className="h-3 bg-slate-900 rounded-full overflow-hidden border border-slate-800 p-0.5">
          <motion.div
            className="h-full bg-gradient-to-r from-blue-500 via-cyan-400 to-emerald-400 rounded-full shadow-[0_0_15px_#06b6d4]"
            initial={{ width: '0%' }}
            animate={{ width: `${overallProgress}%` }}
            transition={{ ease: 'easeOut' }}
          />
        </div>
      </GlassCard>

      <div className="space-y-3">
        {stages.map((stage, idx) => {
          const isActive = stage.status === 'active';
          const isCompleted = stage.status === 'completed';

          return (
            <motion.div
              key={stage.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.05 }}
              className={`pipeline-stage ${isActive ? 'active' : isCompleted ? 'completed' : ''}`}
            >
              <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0">
                {isCompleted ? (
                  <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                ) : isActive ? (
                  <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
                ) : (
                  <div className="w-4 h-4 rounded-full border-2 border-slate-700" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-white">{stage.name}</h4>
                  <StatusBadge status={stage.status} size="sm" />
                </div>
                <p className="text-xs text-slate-400 mt-0.5">{stage.description}</p>

                {isActive && (
                  <div className="mt-2 h-1 bg-slate-800 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-cyan-400"
                      initial={{ width: '0%' }}
                      animate={{ width: `${stage.progress}%` }}
                    />
                  </div>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};
