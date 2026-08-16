import React from 'react';
import { motion } from 'framer-motion';
import { WORKFLOW_STEPS } from '../../constants/mockData';
import { ArrowRight } from 'lucide-react';

export const WorkflowSection: React.FC = () => {
  return (
    <section className="py-24 px-6 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-slate-950/60 to-transparent pointer-events-none" />

      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16 space-y-4"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-purple-500/30 bg-purple-500/5 text-xs font-mono text-purple-400 tracking-wider uppercase">
            Analysis Pipeline
          </div>
          <h2 className="text-3xl md:text-5xl font-black text-white">
            How It{' '}
            <span className="gradient-text">Works</span>
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto text-lg">
            Eight-stage forensic pipeline from upload to final verdict
          </p>
        </motion.div>

        {/* Steps grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {WORKFLOW_STEPS.map((step, i) => (
            <motion.div
              key={step.step}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.07 }}
              className="relative"
            >
              {/* Connector line (desktop) */}
              {i < WORKFLOW_STEPS.length - 1 && i % 4 !== 3 && (
                <div className="hidden lg:block absolute top-8 left-full w-4 z-10">
                  <ArrowRight className="w-4 h-4 text-cyan-500/30" />
                </div>
              )}

              <div className="glass-card p-5 space-y-3 h-full group hover:border-cyan-500/20 transition-all duration-300">
                {/* Step number */}
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-cyan-500/20 flex items-center justify-center flex-shrink-0">
                    <span className="text-xs font-black text-cyan-400 font-mono">{step.step}</span>
                  </div>
                  <div className="flex-1 h-px bg-gradient-to-r from-cyan-500/20 to-transparent" />
                </div>

                <div className="space-y-1.5">
                  <h3 className="text-white font-bold text-sm">{step.title}</h3>
                  <p className="text-slate-500 text-xs leading-relaxed">{step.description}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};
