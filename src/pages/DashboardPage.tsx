import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { StatCard } from '../components/dashboard/StatCard';
import { ActivityFeed } from '../components/dashboard/ActivityFeed';
import { SystemStatus } from '../components/dashboard/SystemStatus';

import { ScanTrendChart } from '../components/charts/ScanTrendChart';
import { RiskDistributionChart } from '../components/charts/RiskDistributionChart';
import { dashboardService } from '../services/dashboardService';
import type { DashboardStats, ActivityItem, SystemStatus as SystemStatusType } from '../types';
import { Shield, Brain, CheckCircle, AlertTriangle, Video, TrendingUp, User } from 'lucide-react';

/**
 * Dashboard Page – main forensic intelligence overview.
 * Stat cards: Total Scans, AI Generated, Authentic, Avg Confidence, Videos Analysed, Risk Alerts.
 */
export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatusType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [s, a, sys] = await Promise.all([
          dashboardService.getStats(),
          dashboardService.getRecentActivity(),
          dashboardService.getSystemStatus(),
        ]);
        setStats(s);
        setActivity(a);
        setSystemStatus(sys);
      } catch (err) {
        console.error('Failed to load dashboard data', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  return (
    <div className="p-6 md:p-10 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs mb-1">
            <Shield className="w-4 h-4" />
            <span>FORENSIC INTELLIGENCE OVERVIEW</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white">Dashboard</h1>
          <p className="text-slate-400 text-sm mt-1">
            Real-time telemetry and digital media authenticity overview
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/profile')}
            className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-cyan-500/40 text-xs font-mono text-cyan-400 flex items-center gap-2 transition-all shadow-sm"
          >
            <User className="w-3.5 h-3.5 text-cyan-400" />
            <span>MY PROFILE</span>
          </button>
          <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-emerald-400 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>LIVE MONITORING</span>
          </div>
        </div>
      </div>

      {/* Stat Cards – 6 cards (3+3) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        <StatCard
          title="Total Media Scans"
          value={stats?.totalScans ?? 0}
          icon={<Shield className="w-5 h-5" />}
          trend={stats?.weeklyGrowth ?? 0}
          trendLabel={`${stats?.todayScans ?? 0} scans today`}
          color="#3b82f6"
          delay={0.05}
        />
        <StatCard
          title="AI / Fake Detected"
          value={stats?.aiGeneratedMedia ?? 0}
          icon={<Brain className="w-5 h-5" />}
          trend={0}
          trendLabel={`${stats?.totalScans ? ((stats.aiGeneratedMedia / stats.totalScans) * 100).toFixed(0) : 0}% of total scans`}
          color="#8b5cf6"
          delay={0.1}
        />
        <StatCard
          title="Authentic Verified"
          value={stats?.authenticMedia ?? 0}
          icon={<CheckCircle className="w-5 h-5" />}
          trend={0}
          trendLabel={`${stats?.totalScans ? ((stats.authenticMedia / stats.totalScans) * 100).toFixed(0) : 0}% of total scans`}
          color="#10b981"
          delay={0.15}
        />
        <StatCard
          title="Average Confidence"
          value={stats?.averageConfidence ?? 0}
          suffix="%"
          decimals={1}
          icon={<TrendingUp className="w-5 h-5" />}
          trend={0}
          trendLabel="Across all neural models"
          color="#06b6d4"
          delay={0.2}
        />
        <StatCard
          title="Videos Analysed"
          value={stats?.videosAnalysed ?? 0}
          icon={<Video className="w-5 h-5" />}
          trend={0}
          trendLabel="Video forensics pipeline"
          color="#f59e0b"
          delay={0.25}
        />
        <StatCard
          title="Risk Alerts"
          value={stats?.riskAlerts ?? 0}
          icon={<AlertTriangle className="w-5 h-5" />}
          trend={0}
          trendLabel="HIGH + CRITICAL risk files"
          color="#ef4444"
          delay={0.3}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ScanTrendChart />
        </div>
        <div>
          <RiskDistributionChart />
        </div>
      </div>

      {/* Activity + System Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ActivityFeed items={activity} loading={loading} />
        </div>
        <div>
          {systemStatus && <SystemStatus data={systemStatus} loading={loading} />}
        </div>
      </div>
    </div>
  );
};
