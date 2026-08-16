import React from 'react';
import { motion } from 'framer-motion';
import { SectionHeader } from '../common/SectionHeader';
import { GlassCard } from '../common/GlassCard';
import { TEAM_MEMBERS } from '../../constants/mockData';
import { Code, Globe } from 'lucide-react';

export const TeamSection: React.FC = () => {
  return (
    <section className="py-20 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <SectionHeader
          eyebrow="ENGINEERING TEAM"
          title="Designed & Developed By"
          description="Built by researchers and engineers passionate about digital integrity and media security."
          center
          className="mb-16"
        />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
          {TEAM_MEMBERS.map((member, idx) => (
            <motion.div
              key={member.id}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.08 }}
            >
              <GlassCard hover className="p-6 text-center space-y-4 border border-slate-800">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-white font-bold text-2xl mx-auto shadow-lg shadow-cyan-500/20">
                  {member.avatar}
                </div>
                <div>
                  <h4 className="text-lg font-bold text-white">{member.name}</h4>
                  <p className="text-cyan-400 text-xs font-mono font-medium mt-0.5">{member.role}</p>
                  <p className="text-slate-500 text-xs mt-1">{member.department}</p>
                </div>
                <div className="flex items-center justify-center gap-3 pt-2">
                  <a href={member.github} className="text-slate-500 hover:text-white transition-colors" aria-label="Code repository">
                    <Code className="w-4 h-4" />
                  </a>
                  <a href={member.linkedin} className="text-slate-500 hover:text-cyan-400 transition-colors" aria-label="Website">
                    <Globe className="w-4 h-4" />
                  </a>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};
