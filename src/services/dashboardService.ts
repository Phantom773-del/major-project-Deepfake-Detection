import { MOCK_SYSTEM_STATUS } from '../constants/mockData';
import type { DashboardStats, ActivityItem, SystemStatus } from '../types';
import { getStoredStats, getStoredActivity } from './dashboardStore';

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const dashboardService = {
  async getStats(): Promise<DashboardStats> {
    await delay(300);
    return getStoredStats();
  },

  async getRecentActivity(limit = 8): Promise<ActivityItem[]> {
    await delay(300);
    const activity = getStoredActivity();
    return activity.slice(0, limit);
  },

  async getSystemStatus(): Promise<SystemStatus> {
    await delay(200);
    return MOCK_SYSTEM_STATUS;
  },
};
