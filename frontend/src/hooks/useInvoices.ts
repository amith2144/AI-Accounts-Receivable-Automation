import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { invoiceService, InvoiceQueryParams } from '@/services/invoiceService';

export function useInvoices(initialParams: InvoiceQueryParams = {}) {
  const queryClient = useQueryClient();
  const [params, setParams] = useState<InvoiceQueryParams>(initialParams);

  const invoicesQuery = useQuery({
    queryKey: ['invoices', params],
    queryFn: () => invoiceService.getInvoices(params),
    staleTime: 5000,
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => invoiceService.uploadInvoiceDocument(file),
  });

  const confirmImportMutation = useMutation({
    mutationFn: ({ documentId, data }: { documentId: string; data: any }) =>
      invoiceService.confirmImport(documentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const voidMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      invoiceService.voidInvoice(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  return {
    invoices: invoicesQuery.data?.items || [],
    total: invoicesQuery.data?.total || 0,
    isLoading: invoicesQuery.isLoading,
    params,
    setParams,
    refetch: invoicesQuery.refetch,
    uploadInvoice: uploadMutation,
    confirmImport: confirmImportMutation,
    voidInvoice: voidMutation,
  };
}
