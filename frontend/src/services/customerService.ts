import apiClient from './api';
import { Customer } from '@/types';

export const customerService = {
  async getCustomers(search?: string): Promise<{ items: Customer[]; total: number }> {
    const res = await apiClient.get<{ items: Customer[]; total: number }>('/customers', {
      params: search ? { search } : undefined,
    });
    return res.data;
  },

  async getCustomerById(id: string): Promise<Customer> {
    const res = await apiClient.get<Customer>(`/customers/${id}`);
    return res.data;
  },

  async createCustomer(data: {
    name: string;
    email: string;
    phone?: string;
    payment_terms_days?: number;
  }): Promise<Customer> {
    const res = await apiClient.post<Customer>('/customers', data);
    return res.data;
  },

  async updateCustomer(
    id: string,
    data: {
      name?: string;
      email?: string;
      phone?: string;
      payment_terms_days?: number;
      reminder_paused?: boolean;
    }
  ): Promise<Customer> {
    const res = await apiClient.put<Customer>(`/customers/${id}`, data);
    return res.data;
  },
};
