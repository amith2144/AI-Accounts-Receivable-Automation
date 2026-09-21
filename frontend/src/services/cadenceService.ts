import apiClient from './api';
import { ReminderCadence, CollectionActivity, CadenceDispatchSummary } from '@/types';

export const cadenceService = {
  async getCadences(): Promise<ReminderCadence[]> {
    const res = await apiClient.get<ReminderCadence[]>('/cadences');
    return res.data;
  },

  async updateCadence(
    id: string,
    data: Partial<ReminderCadence>
  ): Promise<ReminderCadence> {
    const res = await apiClient.put<ReminderCadence>(`/cadences/${id}`, data);
    return res.data;
  },

  async createCadence(data: Omit<ReminderCadence, 'id' | 'created_at' | 'updated_at'>): Promise<ReminderCadence> {
    const res = await apiClient.post<ReminderCadence>('/cadences', data);
    return res.data;
  },

  async triggerRun(): Promise<CadenceDispatchSummary> {
    const res = await apiClient.post<CadenceDispatchSummary>('/cadences/trigger-run');
    return res.data;
  },

  async getActivities(params: {
    activity_type?: string;
    customer_id?: string;
    invoice_id?: string;
    limit?: number;
    offset?: number;
  } = {}): Promise<{ items: CollectionActivity[]; total: number }> {
    const res = await apiClient.get<{ items: CollectionActivity[]; total: number }>('/activities', {
      params,
    });
    return res.data;
  },
};
