import type { DashboardStats, ActivityItem, Verdict, RiskLevel, MediaType } from '../types';

const STATS_KEY = 'phantom_dashboard_stats';
const ACTIVITY_KEY = 'phantom_recent_activity';

const initialStats: DashboardStats = {
  totalScans: 0,
  aiGeneratedMedia: 0,
  authenticMedia: 0,
  averageConfidence: 0,
  todayScans: 0,
  weeklyGrowth: 0,
  videosAnalysed: 0,
  riskAlerts: 0,
};

export const getStoredStats = (): DashboardStats => {
  try {
    const data = localStorage.getItem(STATS_KEY);
    if (data) {
      const parsed = JSON.parse(data);
      // Ensure new fields are present for backward compat
      return { ...initialStats, ...parsed };
    }
  } catch (e) {
    // fallback
  }
  return initialStats;
};

export const getStoredActivity = (): ActivityItem[] => {
  try {
    const data = localStorage.getItem(ACTIVITY_KEY);
    if (data) return JSON.parse(data);
  } catch (e) {
    // fallback
  }
  return [];
};

export const clearStoredData = () => {
  try {
    localStorage.removeItem(STATS_KEY);
    localStorage.removeItem(ACTIVITY_KEY);
  } catch (e) {
    console.error('Failed to clear stats', e);
  }
};

export const recordCompletedScan = (scan: {
  fileName: string;
  verdict: Verdict;
  confidenceScore: number;
  mediaType: MediaType;
  riskLevel: RiskLevel;
  reportId?: string;
}) => {
  const currentStats = getStoredStats();
  const currentActivity = getStoredActivity();

  const newTotal = currentStats.totalScans + 1;
  const newAuthentic = currentStats.authenticMedia + (scan.verdict === 'AUTHENTIC' ? 1 : 0);
  const newAiGenerated = currentStats.aiGeneratedMedia + (
    scan.verdict === 'AI_GENERATED' || scan.verdict === 'MANIPULATED' || scan.verdict === 'SUSPICIOUS' ? 1 : 0
  );
  const newToday = currentStats.todayScans + 1;
  const newVideos = (currentStats.videosAnalysed ?? 0) + (scan.mediaType === 'video' ? 1 : 0);
  const newRiskAlerts = (currentStats.riskAlerts ?? 0) + (
    scan.riskLevel === 'HIGH' || scan.riskLevel === 'CRITICAL' ? 1 : 0
  );

  // Calculate new rolling average confidence
  const prevSum = currentStats.averageConfidence * currentStats.totalScans;
  const newAvgConfidence = parseFloat(((prevSum + scan.confidenceScore) / newTotal).toFixed(1));

  const updatedStats: DashboardStats = {
    totalScans: newTotal,
    authenticMedia: newAuthentic,
    aiGeneratedMedia: newAiGenerated,
    averageConfidence: newAvgConfidence,
    todayScans: newToday,
    weeklyGrowth: parseFloat(((newTotal / Math.max(1, currentStats.totalScans)) * 100 - 100).toFixed(1)),
    videosAnalysed: newVideos,
    riskAlerts: newRiskAlerts,
  };

  const newActivityItem: ActivityItem = {
    id: `ACT-${Date.now()}`,
    fileName: scan.fileName,
    verdict: scan.verdict,
    confidenceScore: scan.confidenceScore,
    timestamp: new Date().toISOString(),
    mediaType: scan.mediaType,
    riskLevel: scan.riskLevel,
    reportId: scan.reportId,
  };

  const updatedActivity = [newActivityItem, ...currentActivity].slice(0, 50);

  try {
    localStorage.setItem(STATS_KEY, JSON.stringify(updatedStats));
    localStorage.setItem(ACTIVITY_KEY, JSON.stringify(updatedActivity));
  } catch (e) {
    console.error('Failed to save scan stats to localStorage', e);
  }
};
