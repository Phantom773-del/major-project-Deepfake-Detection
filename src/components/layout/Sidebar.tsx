import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield, LayoutDashboard, Upload, BarChart3,
  FileText, ChevronLeft, ChevronRight,
  History, Settings, User,
} from 'lucide-react';

/**
 * Sidebar navigation.
 * Includes all spec-required items: Dashboard, Upload, Reports, Scan History, Analytics, Settings, Profile.
 * Collapsible on desktop; icon-only mode when collapsed.
 */

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', href: '/dashboard' },
  { icon: Upload, label: 'Upload & Scan', href: '/upload' },
  { icon: FileText, label: 'Reports', href: '/report/RPT-2024-001847' },
  { icon: History, label: 'Scan History', href: '/scan-history' },
  { icon: BarChart3, label: 'Analytics', href: '/analytics' },
];

const bottomItems = [
  { icon: User, label: 'Profile', href: '/profile' },
  { icon: Settings, label: 'Settings', href: '/settings' },
];

export const Sidebar: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  const isActive = (href: string) => {
    if (href === '/report/RPT-2024-001847') {
      return location.pathname.startsWith('/report');
    }
    return location.pathname === href;
  };

  const NavItem = ({ icon: Icon, label, href }: { icon: typeof LayoutDashboard; label: string; href: string }) => {
    const active = isActive(href);
    return (
      <Link to={href} title={collapsed ? label : undefined}>
        <motion.div
          className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group relative ${
            active
              ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shadow-[0_0_15px_rgba(6,182,212,0.08)]'
              : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/50'
          }`}
          whileHover={{ x: collapsed ? 0 : 2 }}
          transition={{ duration: 0.15 }}
        >
          <Icon className={`w-5 h-5 flex-shrink-0 ${active ? 'text-cyan-400' : 'group-hover:text-slate-300'}`} />
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.2 }}
                className="text-sm font-medium whitespace-nowrap overflow-hidden"
              >
                {label}
              </motion.span>
            )}
          </AnimatePresence>
          {active && !collapsed && (
            <div className="ml-auto w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_#06b6d4] flex-shrink-0" />
          )}
        </motion.div>
      </Link>
    );
  };

  return (
    <motion.aside
      animate={{ width: collapsed ? 72 : 240 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className="sidebar h-screen flex-shrink-0 flex flex-col overflow-hidden relative z-30"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-slate-800/60">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 via-cyan-400 to-purple-500 flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-500/20">
          <Shield className="w-5 h-5 text-white" />
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ delay: 0.05 }}
              className="leading-tight overflow-hidden"
            >
              <div>
                <span className="text-white font-black text-xs tracking-widest">PHANTOM</span>
                <span className="gradient-text font-black text-xs tracking-widest ml-1">PHOENIX</span>
              </div>
              <p className="text-slate-600 text-[10px] font-mono tracking-wide mt-0.5">AI FORENSIC INTEL</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Main Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map(item => (
          <NavItem key={item.href} {...item} />
        ))}
      </nav>

      {/* Bottom Nav */}
      <div className="px-3 py-4 border-t border-slate-800/60 space-y-1">
        {bottomItems.map(item => (
          <NavItem key={item.href} {...item} />
        ))}
        <div className="flex items-center gap-2 px-3 py-2 mt-1">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse flex-shrink-0" />
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-[11px] text-slate-600 font-mono whitespace-nowrap"
              >
                SYSTEM ONLINE
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Collapse Toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3.5 top-20 w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400 hover:text-white hover:border-cyan-500/40 hover:bg-slate-700 transition-all z-10 shadow-lg"
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
      </button>
    </motion.aside>
  );
};
