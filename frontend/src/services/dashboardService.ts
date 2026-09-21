import apiClient from './api';
import {
  DashboardMetrics,
  AgingDistribution,
  CollectionActivity,
  CadenceDispatchSummary,
} from '@/types';

export const dashboardService = {
  async getMetrics(): Promise<DashboardMetrics> {
    const res = await apiClient.get<DashboardMetrics>('/dashboard/metrics');
    return res.data;
  },

  async getAgingDistribution(): Promise<AgingDistribution> {
    const res = await apiClient.get<AgingDistribution>('/dashboard/aging');
    return res.data;
  },

  async getRecentActivity(limit = 10): Promise<{ items: CollectionActivity[]; total: number }> {
    const res = await apiClient.get<{ items: CollectionActivity[]; total: number }>(
      `/dashboard/recent-activity?limit=${limit}`
    );
    return res.data;
  },

  async triggerCadenceRun(): Promise<CadenceDispatchSummary> {
    const res = await apiClient.post<CadenceDispatchSummary>('/cadences/trigger-run');
    return res.data;
  },
};
