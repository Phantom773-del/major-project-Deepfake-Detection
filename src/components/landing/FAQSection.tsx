import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, HelpCircle } from 'lucide-react';
import { FAQ_ITEMS } from '../../constants/mockData';
import { Link } from 'react-router-dom';

export const FAQSection: React.FC = () => {
  const [open, setOpen] = useState<string | null>('1');

  return (
    <section className="py-24 px-6 relative overflow-hidden">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16 space-y-4"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-cyan-500/30 bg-cyan-500/5 text-xs font-mono text-cyan-400 tracking-wider uppercase">
            <HelpCircle className="w-3.5 h-3.5" />
            FAQ
          </div>
          <h2 className="text-3xl md:text-5xl font-black text-white">
            Frequently Asked{' '}
            <span className="gradient-text">Questions</span>
          </h2>
        </motion.div>

        {/* FAQ Accordion */}
        <div className="space-y-3">
          {FAQ_ITEMS.map((item, i) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.06 }}
              className="glass-card border border-slate-800/60 overflow-hidden"
            >
              <button
                onClick={() => setOpen(open === item.id ? null : item.id)}
                className="w-full flex items-center justify-between gap-4 px-6 py-5 text-left"
              >
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-cyan-500/60 font-bold w-5 flex-shrink-0">
                    {item.id.padStart(2, '0')}
                  </span>
                  <span className={`font-semibold text-sm transition-colors ${open === item.id ? 'text-white' : 'text-slate-300'}`}>
                    {item.question}
                  </span>
                </div>
                <motion.div
                  animate={{ rotate: open === item.id ? 180 : 0 }}
                  transition={{ duration: 0.2 }}
                  className="flex-shrink-0 text-slate-500"
                >
                  <ChevronDown className="w-5 h-5" />
                </motion.div>
              </button>

              <AnimatePresence>
                {open === item.id && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.25, ease: 'easeInOut' }}
                    className="overflow-hidden"
                  >
                    <p className="px-6 pb-5 text-slate-400 text-sm leading-relaxed pl-14">
                      {item.answer}
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mt-16 text-center space-y-4"
        >
          <p className="text-slate-500 text-sm">Ready to verify your media?</p>
          <Link to="/upload">
            <motion.button
              whileHover={{ scale: 1.03, boxShadow: '0 0 30px rgba(6,182,212,0.2)' }}
              whileTap={{ scale: 0.98 }}
              className="btn-primary px-10 py-4 rounded-xl font-bold text-base"
            >
              Run Forensic Analysis →
            </motion.button>
          </Link>
        </motion.div>
      </div>
    </section>
  );
};
