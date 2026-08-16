import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Shield, ArrowRight, BarChart3, Upload } from 'lucide-react';

export const CTASection: React.FC = () => {
  return (
    <section className="py-24 px-6 relative overflow-hidden">
      {/* Glowing background */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-[700px] h-[350px] rounded-full bg-blue-600/10 blur-3xl" />
        <div className="absolute w-[500px] h-[250px] rounded-full bg-cyan-500/8 blur-3xl" />
      </div>

      <div className="max-w-4xl mx-auto relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="glass-card p-12 md:p-16 text-center border border-cyan-500/10 hover:border-cyan-500/20 transition-all duration-500"
        >
          {/* Shield Logo */}
          <div className="flex justify-center mb-8">
            <div className="relative">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500 via-cyan-400 to-purple-500 flex items-center justify-center shadow-2xl shadow-cyan-500/20">
                <Shield className="w-10 h-10 text-white" />
              </div>
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-blue-500/30 to-cyan-400/30 blur-xl animate-pulse" />
            </div>
          </div>

          <h2 className="text-3xl md:text-5xl font-black text-white mb-4">
            Start Verifying{' '}
            <span className="gradient-text">Media Authenticity</span>
          </h2>
          <p className="text-slate-400 text-lg max-w-xl mx-auto mb-10 leading-relaxed">
            Upload any image or video and get a comprehensive forensic intelligence report
            in under 4 seconds. Powered by ensemble neural networks.
          </p>

          {/* Stats */}
          <div className="flex flex-wrap justify-center gap-8 mb-10">
            {[
              { value: '97.3%', label: 'Accuracy' },
              { value: '< 4s', label: 'Analysis Time' },
              { value: 'Free', label: 'No Account Needed' },
            ].map(s => (
              <div key={s.label} className="text-center">
                <div className="text-2xl font-black gradient-text">{s.value}</div>
                <div className="text-xs text-slate-500 font-mono mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-wrap justify-center gap-4">
            <Link to="/upload">
              <motion.button
                whileHover={{ scale: 1.04, boxShadow: '0 0 40px rgba(6,182,212,0.3)' }}
                whileTap={{ scale: 0.97 }}
                className="btn-primary flex items-center gap-2 px-8 py-4 rounded-xl text-base font-bold"
              >
                <Upload className="w-5 h-5" />
                Upload & Scan Now
                <ArrowRight className="w-4 h-4" />
              </motion.button>
            </Link>
            <Link to="/dashboard">
              <motion.button
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.97 }}
                className="btn-secondary flex items-center gap-2 px-8 py-4 rounded-xl text-base font-semibold"
              >
                <BarChart3 className="w-5 h-5" />
                View Dashboard
              </motion.button>
            </Link>
          </div>

          <p className="text-xs text-slate-600 mt-8 font-mono">
            No account required · Files processed in isolated memory · Auto-deleted after analysis
          </p>
        </motion.div>
      </div>
    </section>
  );
};
