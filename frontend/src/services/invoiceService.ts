import apiClient from './api';
import {
  Invoice,
  DocumentUploadResponse,
  DocumentImportStatus,
} from '@/types';

export interface InvoiceQueryParams {
  status?: string;
  customer_id?: string;
  aging_bucket?: string;
  offset?: number;
  limit?: number;
}

export const invoiceService = {
  async getInvoices(params: InvoiceQueryParams = {}): Promise<{ items: Invoice[]; total: number }> {
    const res = await apiClient.get<{ items: Invoice[]; total: number }>('/invoices', { params });
    return res.data;
  },

  async getInvoiceById(id: string): Promise<Invoice> {
    const res = await apiClient.get<Invoice>(`/invoices/${id}`);
    return res.data;
  },

  async createInvoice(data: any): Promise<Invoice> {
    const res = await apiClient.post<Invoice>('/invoices', data);
    return res.data;
  },

  async voidInvoice(id: string, reason?: string): Promise<Invoice> {
    const res = await apiClient.post<Invoice>(`/invoices/${id}/void`, { reason });
    return res.data;
  },

  async uploadInvoiceDocument(file: File): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post<DocumentUploadResponse>('/invoices/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  async getImportStatus(documentId: string): Promise<DocumentImportStatus> {
    const res = await apiClient.get<DocumentImportStatus>(`/invoices/import-status/${documentId}`);
    return res.data;
  },

  async confirmImport(documentId: string, confirmedData: any): Promise<Invoice> {
    const res = await apiClient.post<Invoice>(`/invoices/confirm-import/${documentId}`, confirmedData);
    return res.data;
  },
};
