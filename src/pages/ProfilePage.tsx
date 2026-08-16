import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  User, Mail, Phone, Shield, Key, CheckCircle2, Lock,
  Copy, Edit3, Save, RefreshCw, Award, Activity, FileCheck, Check
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';

export const ProfilePage: React.FC = () => {
  const { user, socialLogin } = useAuth();

  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(user?.name || 'Sreeraksha');
  const [email, setEmail] = useState(user?.email || 'sreeraksha452@gmail.com');
  const [phone, setPhone] = useState(user?.phone || '+1 (555) 019-9234');
  const [organization, setOrganization] = useState('Cyber Forensic Labs Ltd.');
  const [role] = useState('Senior Forensic Lead');

  const [twoFactor, setTwoFactor] = useState(true);
  const [copiedKey, setCopiedKey] = useState(false);
  const [apiKey, setApiKey] = useState('pp_live_9948274a108e92bc471d8820f82');

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    setIsEditing(false);
    toast.success('Profile information updated successfully!');
  };

  const handleCopyKey = () => {
    navigator.clipboard.writeText(apiKey);
    setCopiedKey(true);
    toast.success('API Key copied to clipboard');
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const handleRegenerateKey = () => {
    const newKey = `pp_live_${Math.random().toString(36).substring(2, 15)}${Math.random().toString(36).substring(2, 15)}`;
    setApiKey(newKey);
    toast.success('New API Key generated successfully');
  };

  return (
    <div className="p-6 md:p-10 space-y-8 max-w-6xl mx-auto">
      {/* Header Banner */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-6 md:p-8 relative overflow-hidden border border-slate-800"
      >
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/10 rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-purple-500/10 rounded-full blur-[100px] pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row items-center md:items-start gap-6">
          {/* Avatar */}
          <div className="relative group">
            <div className="w-24 h-24 rounded-2xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-purple-600 flex items-center justify-center text-white text-3xl font-extrabold shadow-xl shadow-cyan-500/20 ring-4 ring-slate-900">
              {name.charAt(0).toUpperCase()}
            </div>
            <div className="absolute -bottom-2 -right-2 bg-emerald-500 text-slate-950 p-1.5 rounded-full ring-4 ring-slate-900" title="Account Verified">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>

          {/* User Brief */}
          <div className="flex-1 text-center md:text-left space-y-2">
            <div className="flex flex-wrap items-center justify-center md:justify-start gap-3">
              <h1 className="text-2xl md:text-3xl font-black text-white">{name}</h1>
              <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-mono">
                {role}
              </span>
            </div>
            <p className="text-slate-400 text-sm">{organization}</p>
            <div className="flex flex-wrap items-center justify-center md:justify-start gap-4 text-xs text-slate-400 pt-1 font-mono">
              <span className="flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-cyan-400" /> {email}
              </span>
              <span className="flex items-center gap-1.5">
                <Phone className="w-3.5 h-3.5 text-cyan-400" /> {phone}
              </span>
            </div>
          </div>

          {/* Action button */}
          <button
            onClick={() => setIsEditing(!isEditing)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white font-medium text-sm transition-all shadow-lg"
          >
            {isEditing ? <Save className="w-4 h-4 text-cyan-400" /> : <Edit3 className="w-4 h-4 text-cyan-400" />}
            {isEditing ? 'Cancel Edit' : 'Edit Profile'}
          </button>
        </div>
      </motion.div>

      {/* Investigator Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Forensic Scans', value: '142', icon: Activity, color: 'text-cyan-400', border: 'border-cyan-500/20' },
          { label: 'Deepfakes Detected', value: '28', icon: Shield, color: 'text-red-400', border: 'border-red-500/20' },
          { label: 'Verified Authentic', value: '114', icon: FileCheck, color: 'text-emerald-400', border: 'border-emerald-500/20' },
          { label: 'Security Clearance', value: 'Level 4 (Elite)', icon: Award, color: 'text-purple-400', border: 'border-purple-500/20' },
        ].map((stat, idx) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05 }}
            className={`glass-card p-5 border ${stat.border} flex items-center gap-4`}
          >
            <div className={`p-3 rounded-xl bg-slate-900 border border-slate-800 ${stat.color}`}>
              <stat.icon className="w-6 h-6" />
            </div>
            <div>
              <p className="text-slate-400 text-xs font-mono">{stat.label}</p>
              <p className="text-xl font-bold text-white mt-0.5">{stat.value}</p>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Cols: Profile Form & Credentials */}
        <div className="lg:col-span-2 space-y-6">
          {/* Profile Edit / Information */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-6 border border-slate-800 space-y-6"
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                  <User className="w-4 h-4" />
                </div>
                <h2 className="text-white font-bold text-lg">Personal Details</h2>
              </div>
            </div>

            <form onSubmit={handleSaveProfile} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">Full Name</label>
                  <input
                    type="text"
                    disabled={!isEditing}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-900/60 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-cyan-500 disabled:opacity-75 disabled:cursor-not-allowed"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">Email Address</label>
                  <input
                    type="email"
                    disabled={!isEditing}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-900/60 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-cyan-500 disabled:opacity-75 disabled:cursor-not-allowed"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">Phone Number</label>
                  <input
                    type="text"
                    disabled={!isEditing}
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-900/60 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-cyan-500 disabled:opacity-75 disabled:cursor-not-allowed"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">Organization</label>
                  <input
                    type="text"
                    disabled={!isEditing}
                    value={organization}
                    onChange={(e) => setOrganization(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-900/60 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-cyan-500 disabled:opacity-75 disabled:cursor-not-allowed"
                  />
                </div>
              </div>

              {isEditing && (
                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    className="flex items-center gap-2 px-5 py-2.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 rounded-xl font-bold text-sm transition-all shadow-lg shadow-cyan-500/20"
                  >
                    <Save className="w-4 h-4" /> Save Changes
                  </button>
                </div>
              )}
            </form>
          </motion.div>

          {/* API Keys & Tokens */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-6 border border-slate-800 space-y-6"
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                  <Key className="w-4 h-4" />
                </div>
                <h2 className="text-white font-bold text-lg">Forensic API Token</h2>
              </div>
              <button
                onClick={handleRegenerateKey}
                className="flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 transition-colors font-mono"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Regenerate Key
              </button>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              Use this bearer token to integrate Phantom Phoenix AI forensic scanning into your automated CI/CD security pipelines or custom scripts.
            </p>

            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={apiKey}
                className="flex-1 px-3.5 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-cyan-400 font-mono text-xs focus:outline-none"
              />
              <button
                onClick={handleCopyKey}
                className="flex items-center gap-1.5 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white rounded-xl text-xs font-semibold transition-all"
              >
                {copiedKey ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-cyan-400" />}
                {copiedKey ? 'Copied' : 'Copy'}
              </button>
            </div>
          </motion.div>
        </div>

        {/* Right 1 Col: Security & Connected Accounts */}
        <div className="space-y-6">
          {/* Connected Accounts */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-6 border border-slate-800 space-y-5"
          >
            <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
              <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                <Shield className="w-4 h-4" />
              </div>
              <h2 className="text-white font-bold text-lg">Connected Accounts</h2>
            </div>

            <div className="space-y-3">
              {/* Google */}
              <div className="flex items-center justify-between p-3.5 bg-slate-900/60 border border-slate-800 rounded-xl">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
                    <svg className="w-4 h-4" viewBox="0 0 24 24">
                      <path fill="#EA4335" d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.7 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.3 9 5 12 5z" />
                      <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z" />
                      <path fill="#FBBC05" d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.3s.2-1.6.4-2.3L1.9 7.3C.7 9.7 0 12 0 14.8c0 2.7.7 5.1 1.9 7.5l3.7-2.9z" />
                      <path fill="#34A853" d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.3-6.4-5.2L1.9 16c1.8 3.7 5.6 7 10.1 7z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-white">Google</p>
                    <p className="text-[10px] text-emerald-400 font-mono">Connected</p>
                  </div>
                </div>
                <button
                  onClick={() => socialLogin('Google')}
                  className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 rounded-lg transition-all"
                >
                  Sync
                </button>
              </div>

              {/* GitHub */}
              <div className="flex items-center justify-between p-3.5 bg-slate-900/60 border border-slate-800 rounded-xl">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
                    <svg className="w-4 h-4 fill-current text-white" viewBox="0 0 24 24">
                      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-white">GitHub</p>
                    <p className="text-[10px] text-emerald-400 font-mono">Connected</p>
                  </div>
                </div>
                <button
                  onClick={() => socialLogin('GitHub')}
                  className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 rounded-lg transition-all"
                >
                  Sync
                </button>
              </div>
            </div>
          </motion.div>

          {/* Security Overview */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-6 border border-slate-800 space-y-5"
          >
            <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
              <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                <Lock className="w-4 h-4" />
              </div>
              <h2 className="text-white font-bold text-lg">Security & Privacy</h2>
            </div>

            <div className="space-y-4 text-xs">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-white">2-Factor Authentication (2FA)</p>
                  <p className="text-slate-400 text-[11px]">Require authenticator app on login</p>
                </div>
                <button
                  onClick={() => {
                    setTwoFactor(!twoFactor);
                    toast.success(`2FA has been ${!twoFactor ? 'enabled' : 'disabled'}`);
                  }}
                  className={`relative w-10 h-5 rounded-full transition-colors duration-200 ${twoFactor ? 'bg-cyan-500' : 'bg-slate-700'}`}
                >
                  <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200 ${twoFactor ? 'translate-x-5' : 'translate-x-0.5'}`} />
                </button>
              </div>

              <div className="pt-2 border-t border-slate-800/80">
                <p className="font-semibold text-white mb-1">Active Session</p>
                <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl space-y-1 font-mono text-[11px] text-slate-400">
                  <div className="flex justify-between">
                    <span>IP Address:</span>
                    <span className="text-cyan-400">192.168.1.104</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Location:</span>
                    <span className="text-slate-300">Bangalore, IN</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Status:</span>
                    <span className="text-emerald-400">Active Now</span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};
