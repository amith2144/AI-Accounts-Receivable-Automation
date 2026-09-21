import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { dashboardService } from '@/services/dashboardService';

export function useDashboard() {
  const queryClient = useQueryClient();

  const metricsQuery = useQuery({
    queryKey: ['dashboard', 'metrics'],
    queryFn: () => dashboardService.getMetrics(),
    staleTime: 10000,
  });

  const agingQuery = useQuery({
    queryKey: ['dashboard', 'aging'],
    queryFn: () => dashboardService.getAgingDistribution(),
    staleTime: 10000,
  });

  const activityQuery = useQuery({
    queryKey: ['dashboard', 'activity'],
    queryFn: () => dashboardService.getRecentActivity(10),
    staleTime: 10000,
  });

  const triggerCadenceMutation = useMutation({
    mutationFn: () => dashboardService.triggerCadenceRun(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      queryClient.invalidateQueries({ queryKey: ['activities'] });
    },
  });

  return {
    metrics: metricsQuery.data,
    aging: agingQuery.data,
    activity: activityQuery.data?.items || [],
    isLoading: metricsQuery.isLoading || agingQuery.isLoading,
    refetchAll: () => {
      metricsQuery.refetch();
      agingQuery.refetch();
      activityQuery.refetch();
    },
    triggerCadence: triggerCadenceMutation,
  };
}
