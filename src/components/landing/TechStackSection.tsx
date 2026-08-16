import React from 'react';
import { motion } from 'framer-motion';
import { SectionHeader } from '../common/SectionHeader';

const techStack = [
  { name: 'React 19', category: 'Frontend Core' },
  { name: 'TypeScript', category: 'Type Safety' },
  { name: 'Vite', category: 'Build Tool' },
  { name: 'Tailwind CSS', category: 'Styling' },
  { name: 'Framer Motion', category: 'Animations' },
  { name: 'Recharts', category: 'Data Visualization' },
  { name: 'TanStack Query', category: 'State Management' },
  { name: 'Axios', category: 'API Layer' },
  { name: 'React Hook Form', category: 'Forms' },
  { name: 'Zod', category: 'Validation' },
  { name: 'Lucide Icons', category: 'UI Icons' },
  { name: 'shadcn/ui', category: 'Design System' },
];

export const TechStackSection: React.FC = () => {
  return (
    <section className="py-20 bg-slate-950/40 border-y border-slate-800/40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <SectionHeader
          eyebrow="ARCHITECTURE"
          title="Built With Modern Tech Stack"
          description="Engineered using industry-standard React best practices for high performance, maintainability, and scale."
          center
          className="mb-12"
        />

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {techStack.map((tech, idx) => (
            <motion.div
              key={tech.name}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.05 }}
              className="glass-card p-4 text-center border border-slate-800 hover:border-cyan-500/30 transition-colors"
            >
              <h5 className="text-white font-bold text-sm">{tech.name}</h5>
              <p className="text-slate-500 text-[10px] font-mono mt-1 uppercase">{tech.category}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};
