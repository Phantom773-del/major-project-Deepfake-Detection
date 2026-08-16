import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from '../components/layout/Sidebar';
import { TopNavBar } from '../components/layout/TopNavBar';
import { motion } from 'framer-motion';

/**
 * AppLayout – wraps all authenticated app pages with Sidebar + TopNavBar.
 */
export const AppLayout: React.FC = () => {
  return (
    <div className="flex h-screen bg-forensic overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <TopNavBar />
        <main className="flex-1 overflow-y-auto">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="min-h-full"
          >
            <Outlet />
          </motion.div>
        </main>
      </div>
    </div>
  );
};
