import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Bell, User, X, Check, AlertTriangle, Info, CheckCircle, History, BarChart3, LogOut, Settings } from 'lucide-react';
import { MOCK_NOTIFICATIONS } from '../../constants/mockData';
import type { Notification } from '../../types';
import { useAuth } from '../../contexts/AuthContext';

/**
 * TopNavBar – sticky top navigation with search, notifications and user profile.
 * Dropdowns close on outside click.
 */
export const TopNavBar: React.FC = () => {
  const navigate = useNavigate();
  const [searchOpen, setSearchOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>(MOCK_NOTIFICATIONS);
  const [searchQuery, setSearchQuery] = useState('');

  const notifRef = useRef<HTMLDivElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const unreadCount = notifications.filter(n => !n.read).length;

  const markAllRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  };

  const markRead = (id: string) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  };

  const notifIcon = (type: Notification['type']) => {
    switch (type) {
      case 'alert': return <AlertTriangle className="w-4 h-4 text-red-400" />;
      case 'success': return <CheckCircle className="w-4 h-4 text-emerald-400" />;
      case 'warning': return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      default: return <Info className="w-4 h-4 text-cyan-400" />;
    }
  };  const { user, logout } = useAuth();

  return (
    <header className="navbar sticky top-0 z-20 px-4 md:px-6 h-14 flex items-center justify-between gap-4">
      {/* Left: Search */}
      <div className="flex-1 max-w-md">
        {searchOpen ? (
          <motion.div
            initial={{ opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: '100%' }}
            className="relative flex items-center"
          >
            <Search className="w-4 h-4 text-slate-400 absolute left-3" />
            <input
              autoFocus
              type="text"
              placeholder="Search reports, scans, files..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Escape') { setSearchOpen(false); setSearchQuery(''); }
                if (e.key === 'Enter' && searchQuery) { navigate('/scan-history'); setSearchOpen(false); }
              }}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-10 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/60"
            />
            <button
              onClick={() => { setSearchOpen(false); setSearchQuery(''); }}
              className="absolute right-3 text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </motion.div>
        ) : (
          <button
            onClick={() => setSearchOpen(true)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-slate-400 hover:text-slate-300 hover:bg-slate-800/50 transition-all text-sm"
          >
            <Search className="w-4 h-4" />
            <span className="hidden md:block font-mono text-xs">Search reports, scans...</span>
            <kbd className="hidden lg:block ml-auto text-[10px] bg-slate-800 border border-slate-700 rounded px-1.5 py-0.5 text-slate-500">⌘K</kbd>
          </button>
        )}
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-1.5">

        {/* Notifications */}
        <div className="relative" ref={notifRef}>
          <button
            id="notif-btn"
            onClick={() => { setNotifOpen(v => !v); setProfileOpen(false); }}
            className="relative w-9 h-9 flex items-center justify-center rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition-all"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500 ring-2 ring-[#030712]" />
            )}
          </button>

          <AnimatePresence>
            {notifOpen && (
              <motion.div
                initial={{ opacity: 0, y: -8, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.96 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 mt-2 w-80 glass-card border border-slate-800 shadow-2xl overflow-hidden"
              >
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                  <div>
                    <span className="text-sm font-semibold text-white">Notifications</span>
                    {unreadCount > 0 && (
                      <span className="ml-2 px-1.5 py-0.5 text-[10px] rounded-full bg-red-500/20 text-red-400 font-mono">{unreadCount}</span>
                    )}
                  </div>
                  <button
                    onClick={markAllRead}
                    className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
                  >
                    <Check className="w-3 h-3" /> Mark all read
                  </button>
                </div>
                <div className="max-h-72 overflow-y-auto">
                  {notifications.length === 0 ? (
                    <p className="text-center text-slate-500 text-xs p-6">No notifications</p>
                  ) : (
                    notifications.map(n => (
                      <div
                        key={n.id}
                        onClick={() => markRead(n.id)}
                        className={`flex gap-3 px-4 py-3 cursor-pointer transition-colors hover:bg-slate-800/50 border-b border-slate-800/60 last:border-0 ${
                          !n.read ? 'bg-cyan-500/5' : ''
                        }`}
                      >
                        <div className="mt-0.5 flex-shrink-0">{notifIcon(n.type)}</div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold text-white">{n.title}</p>
                          <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">{n.message}</p>
                          <p className="text-[10px] text-slate-600 mt-1 font-mono">{n.time}</p>
                        </div>
                        {!n.read && (
                          <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-1 flex-shrink-0" />
                        )}
                      </div>
                    ))
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* User Profile */}
        <div className="relative" ref={profileRef}>
          <button
            id="profile-btn"
            onClick={() => { setProfileOpen(v => !v); setNotifOpen(false); }}
            className="flex items-center gap-2 pl-2 pr-3 h-9 rounded-lg hover:bg-slate-800/60 transition-all"
          >
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center flex-shrink-0">
              <User className="w-4 h-4 text-white" />
            </div>
            <span className="hidden md:block text-xs font-medium text-slate-300">{user?.name || 'Sreeraksha'}</span>
          </button>

          <AnimatePresence>
            {profileOpen && (
              <motion.div
                initial={{ opacity: 0, y: -8, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.96 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 mt-2 w-56 glass-card border border-slate-800 shadow-2xl overflow-hidden"
              >
                <div className="px-4 py-3 border-b border-slate-800">
                  <p className="text-sm font-semibold text-white">{user?.name || 'Sreeraksha'}</p>
                  <p className="text-xs text-slate-500 font-mono truncate">{user?.email || 'sreeraksha@example.com'}</p>
                </div>
                <div className="py-1">
                  <button
                    onClick={() => { navigate('/profile'); setProfileOpen(false); }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors"
                  >
                    <User className="w-4 h-4 text-cyan-400" />
                    My Profile
                  </button>
                  <button
                    onClick={() => { navigate('/scan-history'); setProfileOpen(false); }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors"
                  >
                    <History className="w-4 h-4 text-slate-500" />
                    Scan History
                  </button>
                  <button
                    onClick={() => { navigate('/analytics'); setProfileOpen(false); }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors"
                  >
                    <BarChart3 className="w-4 h-4 text-slate-500" />
                    Analytics
                  </button>
                  <button
                    onClick={() => { navigate('/settings'); setProfileOpen(false); }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors border-b border-slate-800/60"
                  >
                    <Settings className="w-4 h-4 text-slate-500" />
                    Settings
                  </button>
                  <button
                    onClick={() => { logout(); setProfileOpen(false); navigate('/login'); }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors font-medium"
                  >
                    <LogOut className="w-4 h-4 text-red-400" />
                    Log Out
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
};
