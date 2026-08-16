import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, BarChart3, FileText, Search, User } from 'lucide-react';
import { GlassCard } from '../common/GlassCard';

const actions = [
  { icon: Upload, label: 'New Scan', description: 'Upload media for analysis', href: '/upload', color: '#06b6d4' },
  { icon: User, label: 'My Profile', description: 'Manage account & API keys', href: '/profile', color: '#ec4899' },
  { icon: BarChart3, label: 'Analytics', description: 'View detailed statistics', href: '/analytics', color: '#3b82f6' },
  { icon: FileText, label: 'Reports', description: 'Access forensic reports', href: '/report/RPT-2024-001847', color: '#8b5cf6' },
  { icon: Search, label: 'Scan History', description: 'View previous analyses', href: '/scan-history', color: '#10b981' },
];

export const QuickActions: React.FC = () => {
  const navigate = useNavigate();

  return (
    <GlassCard>
      <h3 className="text-white font-semibold mb-4">Quick Actions</h3>
      <div className="grid grid-cols-2 gap-3">
        {actions.map(({ icon: Icon, label, description, href, color }) => (
          <button
            key={label}
            onClick={() => navigate(href)}
            className="p-3 rounded-xl text-left transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
            style={{
              background: `${color}0d`,
              border: `1px solid ${color}20`,
            }}
          >
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center mb-2"
              style={{ background: `${color}20` }}
            >
              <Icon className="w-4 h-4" style={{ color }} />
            </div>
            <p className="text-white text-sm font-medium">{label}</p>
            <p className="text-slate-500 text-xs mt-0.5">{description}</p>
          </button>
        ))}
      </div>
    </GlassCard>
  );
};
