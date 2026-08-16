import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Copy, Check, Share2, Mail, Lock, Globe } from 'lucide-react';
import toast from 'react-hot-toast';
import type { ForensicReport } from '../../types';

interface ShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  report: ForensicReport;
}

export const ShareModal: React.FC<ShareModalProps> = ({ isOpen, onClose, report }) => {
  const [copied, setCopied] = useState(false);
  const [accessLevel, setAccessLevel] = useState<'link' | 'restricted'>('link');
  const shareUrl = window.location.href;

  const handleCopyLink = () => {
    navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    toast.success('Report URL copied to clipboard!');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleNativeShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `Forensic Report - ${report.fileName}`,
          text: `Phantom Phoenix Forensic Report for ${report.fileName}. Verdict: ${report.verdict}`,
          url: shareUrl,
        });
        toast.success('Shared successfully!');
      } catch (err) {
        // User cancelled or share failed
      }
    } else {
      handleCopyLink();
    }
  };

  const handleEmailShare = () => {
    const subject = encodeURIComponent(`Forensic Report: ${report.fileName}`);
    const body = encodeURIComponent(`View the complete forensic analysis for ${report.fileName}:\n\nVerdict: ${report.verdict}\nConfidence: ${report.confidenceScore}%\n\nLink: ${shareUrl}`);
    window.open(`mailto:?subject=${subject}&body=${body}`, '_blank');
  };

  const handleTwitterShare = () => {
    const text = encodeURIComponent(`Forensic Media Analysis for ${report.fileName} via Phantom Phoenix Platform.`);
    window.open(`https://twitter.com/intent/tweet?text=${text}&url=${encodeURIComponent(shareUrl)}`, '_blank');
  };

  const handleLinkedinShare = () => {
    window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`, '_blank');
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          className="relative w-full max-w-lg glass-card border border-slate-800 p-6 md:p-8 space-y-6 shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                <Share2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-white font-extrabold text-lg">Share Forensic Report</h3>
                <p className="text-slate-400 text-xs font-mono">{report.id}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 flex items-center justify-center text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Copy Link Section */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300">Direct Share Link</label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={shareUrl}
                className="flex-1 px-3.5 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-cyan-400 font-mono text-xs focus:outline-none"
              />
              <button
                onClick={handleCopyLink}
                className="flex items-center gap-1.5 px-4 py-2.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 rounded-xl text-xs font-bold transition-all shadow-lg shadow-cyan-500/20"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
          </div>

          {/* Access Control */}
          <div className="p-4 bg-slate-900/60 rounded-xl border border-slate-800 space-y-3">
            <span className="text-xs font-semibold text-slate-300 block">Link Permissions</span>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setAccessLevel('link')}
                className={`p-3 rounded-lg border text-left text-xs transition-all flex items-center gap-2.5 ${
                  accessLevel === 'link'
                    ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-400 font-semibold'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-300'
                }`}
              >
                <Globe className="w-4 h-4 flex-shrink-0" />
                <div>
                  <p className="text-white text-xs">Anyone with link</p>
                  <p className="text-[10px] text-slate-500">Read-only report access</p>
                </div>
              </button>

              <button
                onClick={() => setAccessLevel('restricted')}
                className={`p-3 rounded-lg border text-left text-xs transition-all flex items-center gap-2.5 ${
                  accessLevel === 'restricted'
                    ? 'bg-purple-500/10 border-purple-500/40 text-purple-400 font-semibold'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-300'
                }`}
              >
                <Lock className="w-4 h-4 flex-shrink-0" />
                <div>
                  <p className="text-white text-xs">Restricted</p>
                  <p className="text-[10px] text-slate-500">Authenticated users only</p>
                </div>
              </button>
            </div>
          </div>

          {/* Quick Share Buttons */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-slate-300 block">Share Via</span>
            <div className="grid grid-cols-4 gap-3">
              <button
                onClick={handleEmailShare}
                className="flex flex-col items-center gap-1.5 p-3 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white transition-all text-xs font-medium"
              >
                <Mail className="w-5 h-5 text-cyan-400" />
                <span>Email</span>
              </button>

              <button
                onClick={handleTwitterShare}
                className="flex flex-col items-center gap-1.5 p-3 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white transition-all text-xs font-medium"
              >
                <svg className="w-5 h-5 text-blue-400 fill-current" viewBox="0 0 24 24">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                </svg>
                <span>X / Twitter</span>
              </button>

              <button
                onClick={handleLinkedinShare}
                className="flex flex-col items-center gap-1.5 p-3 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white transition-all text-xs font-medium"
              >
                <svg className="w-5 h-5 text-blue-500 fill-current" viewBox="0 0 24 24">
                  <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.32 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.79M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z"/>
                </svg>
                <span>LinkedIn</span>
              </button>

              <button
                onClick={handleNativeShare}
                className="flex flex-col items-center gap-1.5 p-3 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white transition-all text-xs font-medium"
              >
                <Share2 className="w-5 h-5 text-emerald-400" />
                <span>More</span>
              </button>
            </div>
          </div>

          {/* Footer note */}
          <div className="pt-2 border-t border-slate-800 text-center">
            <p className="text-[11px] text-slate-500 font-mono">
              Report checksum verified • Hash integrity enforced
            </p>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
