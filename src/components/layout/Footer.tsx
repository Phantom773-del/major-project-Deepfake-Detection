import React from 'react';
import { Link } from 'react-router-dom';
import { Shield, Mail, Code, Globe, MessageSquare } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-forensic border-t border-slate-800/40 py-16 mt-20">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 mb-12">
          {/* Brand */}
          <div className="md:col-span-2">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <div>
                <span className="text-white font-bold text-sm">PHANTOM </span>
                <span className="gradient-text font-bold text-sm">PHOENIX</span>
              </div>
            </div>
            <p className="text-slate-500 text-sm leading-relaxed max-w-xs">
              Digital Media Authenticity & AI Forensic Intelligence Platform. 
              Detect deepfakes, AI-generated content, and image manipulation with precision.
            </p>
            <div className="flex items-center gap-4 mt-6">
              {[Code, Globe, MessageSquare, Mail].map((Icon, i) => (
                <a
                  key={i}
                  href="#"
                  className="w-9 h-9 rounded-lg glass-card flex items-center justify-center text-slate-500 hover:text-cyan-400 hover:border-cyan-500/30 transition-all"
                  aria-label="Social link"
                >
                  <Icon className="w-4 h-4" />
                </a>
              ))}
            </div>
          </div>

          {/* Links */}
          <div>
            <h4 className="text-white font-semibold text-sm mb-4">Platform</h4>
            <div className="space-y-2">
              {['Dashboard', 'Upload & Scan', 'Analytics', 'Reports'].map((link) => (
                <div key={link}>
                  <Link
                    to={`/${link.toLowerCase().replace(' & ', '-').replace(' ', '-')}`}
                    className="text-slate-500 hover:text-cyan-400 text-sm transition-colors"
                  >
                    {link}
                  </Link>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h4 className="text-white font-semibold text-sm mb-4">Research</h4>
            <div className="space-y-2">
              {['AI Detection', 'Frequency Analysis', 'Explainable AI', 'Documentation'].map((link) => (
                <div key={link}>
                  <a href="#" className="text-slate-500 hover:text-cyan-400 text-sm transition-colors">
                    {link}
                  </a>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="border-t border-slate-800/40 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-slate-600 text-xs font-mono">
            © 2024 PHANTOM PHOENIX — Digital Media Forensic Intelligence Platform
          </p>
          <div className="flex items-center gap-2 text-xs font-mono">
            <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            <span className="text-slate-600">ALL SYSTEMS OPERATIONAL</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
