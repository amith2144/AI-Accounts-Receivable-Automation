import apiClient from './api';
import { PaymentRecord, PaymentMethod } from '@/types';

export interface RecordPaymentPayload {
  amount: number;
  payment_date: string;
  payment_method: PaymentMethod;
  reference_number?: string;
  notes?: string;
}

export interface PaymentResultResponse {
  payment: PaymentRecord;
  invoice_id: string;
  invoice_status: string;
  remaining_balance: number | string;
}

export const paymentService = {
  async recordPayment(
    invoiceId: string,
    payload: RecordPaymentPayload
  ): Promise<PaymentResultResponse> {
    const res = await apiClient.post<PaymentResultResponse>(
      `/invoices/${invoiceId}/payments`,
      payload
    );
    return res.data;
  },

  async getPaymentsByInvoice(invoiceId: string): Promise<{ items: PaymentRecord[]; total: number }> {
    const res = await apiClient.get<{ items: PaymentRecord[]; total: number }>(
      `/invoices/${invoiceId}/payments`
    );
    return res.data;
  },
};
