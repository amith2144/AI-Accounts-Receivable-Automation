import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { customerService } from '@/services/customerService';

export function useCustomers() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');

  const customersQuery = useQuery({
    queryKey: ['customers', search],
    queryFn: () => customerService.getCustomers(search || undefined),
    staleTime: 5000,
  });

  const createCustomerMutation = useMutation({
    mutationFn: (data: { name: string; email: string; phone?: string; payment_terms_days?: number }) =>
      customerService.createCustomer(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customers'] });
    },
  });

  const toggleReminderMutation = useMutation({
    mutationFn: ({ id, paused }: { id: string; paused: boolean }) =>
      customerService.updateCustomer(id, { reminder_paused: paused }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customers'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  return {
    customers: customersQuery.data?.items || [],
    total: customersQuery.data?.total || 0,
    isLoading: customersQuery.isLoading,
    search,
    setSearch,
    refetch: customersQuery.refetch,
    createCustomer: createCustomerMutation,
    toggleReminder: toggleReminderMutation,
  };
}
