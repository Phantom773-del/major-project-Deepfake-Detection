import React from 'react';
import { motion } from 'framer-motion';
import { Brain, Database, Activity, Eye, Target, FileText } from 'lucide-react';
import { PLATFORM_FEATURES } from '../../constants/mockData';

const iconMap: Record<string, React.ReactNode> = {
  Brain: <Brain className="w-6 h-6" />,
  Database: <Database className="w-6 h-6" />,
  Activity: <Activity className="w-6 h-6" />,
  Eye: <Eye className="w-6 h-6" />,
  Target: <Target className="w-6 h-6" />,
  FileText: <FileText className="w-6 h-6" />,
};

const colorMap: Record<string, { text: string; bg: string; border: string; glow: string }> = {
  'cyber-blue': { text: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/20', glow: 'group-hover:shadow-blue-500/15' },
  'cyber-cyan': { text: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500/20', glow: 'group-hover:shadow-cyan-500/15' },
  'cyber-purple': { text: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/20', glow: 'group-hover:shadow-purple-500/15' },
  'cyber-green': { text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', glow: 'group-hover:shadow-emerald-500/15' },
  'cyber-amber': { text: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20', glow: 'group-hover:shadow-amber-500/15' },
  'cyber-red': { text: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20', glow: 'group-hover:shadow-red-500/15' },
};

export const FeaturesSection: React.FC = () => {
  return (
    <section className="py-24 px-6 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-blue-950/10 to-transparent pointer-events-none" />

      <div className="max-w-6xl mx-auto">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16 space-y-4"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-cyan-500/30 bg-cyan-500/5 text-xs font-mono text-cyan-400 tracking-wider uppercase">
            Core Capabilities
          </div>
          <h2 className="text-3xl md:text-5xl font-black text-white">
            Forensic Intelligence{' '}
            <span className="gradient-text">Modules</span>
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto text-lg leading-relaxed">
            Six specialized detection and analysis engines working in concert to deliver
            comprehensive media authenticity verdicts.
          </p>
        </motion.div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {PLATFORM_FEATURES.map((feature, i) => {
            const c = colorMap[feature.color] || colorMap['cyber-blue'];
            return (
              <motion.div
                key={feature.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.08 }}
                whileHover={{ y: -4 }}
                className={`glass-card p-6 space-y-4 group border border-slate-800/60 hover:border-slate-700/80 transition-all duration-300 hover:shadow-xl ${c.glow}`}
              >
                {/* Icon */}
                <div className={`w-12 h-12 rounded-xl ${c.bg} border ${c.border} flex items-center justify-center ${c.text} transition-transform duration-300 group-hover:scale-110`}>
                  {iconMap[feature.icon]}
                </div>

                {/* Content */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-mono font-bold tracking-widest ${c.text} uppercase`}>
                      Module {feature.id.padStart(2, '0')}
                    </span>
                    <div className={`flex-1 h-px ${c.bg}`} />
                  </div>
                  <h3 className="text-white font-bold text-lg">{feature.title}</h3>
                  <p className="text-slate-400 text-sm leading-relaxed">{feature.description}</p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
