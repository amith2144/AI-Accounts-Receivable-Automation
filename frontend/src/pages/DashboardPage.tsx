import React, { useState } from 'react';
import { useDashboard } from '@/hooks/useDashboard';
import { useInvoices } from '@/hooks/useInvoices';
import { MetricsCard } from '@/components/dashboard/MetricsCard';
import { AgingChart } from '@/components/dashboard/AgingChart';
import { InflowVelocityChart } from '@/components/dashboard/InflowVelocityChart';
import { CollectionEfficiencyGauge } from '@/components/dashboard/CollectionEfficiencyGauge';
import { CadenceHeatmap } from '@/components/dashboard/CadenceHeatmap';
import { OverdueList } from '@/components/dashboard/OverdueList';
import { RecentActivityList } from '@/components/dashboard/RecentActivityList';
import { Button } from '@/components/ui/button';
import { Dialog } from '@/components/ui/dialog';
import { Invoice } from '@/types';
import { formatCurrency } from '@/lib/utils';
import {
  DollarSign,
  AlertCircle,
  TrendingDown,
  Play,
  CheckCircle2,
  Sparkles,
  Calendar,
  Zap,
} from 'lucide-react';

interface DashboardPageProps {
  onSelectInvoiceForPayment: (invoice: Invoice) => void;
  onNavigateToInvoices: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onSelectInvoiceForPayment,
  onNavigateToInvoices,
}) => {
  const { metrics, aging, activity, triggerCadence } = useDashboard();
  const { invoices } = useInvoices();
  const [dispatchResult, setDispatchResult] = useState<any | null>(null);

  const handleTriggerCadence = async () => {
    try {
      const res = await triggerCadence.mutateAsync();
      setDispatchResult(res);
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to trigger cadence execution.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Bar Action Ribbon: Solid Piano-Black Lacquer Glaze */}
      <div className="rounded-2xl piano-black-card p-4 sm:p-5 relative overflow-hidden">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 relative z-10">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-600/30 shrink-0 border border-blue-400/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm sm:text-base font-semibold text-white tracking-tight">
                  Autonomous Collection Orchestrator
                </h2>
                <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-blue-500/15 text-blue-300 border border-blue-500/25">
                  <Zap className="w-2.5 h-2.5" /> Engine v1.0
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5 leading-snug">
                Evaluates past-due aging buckets, throttles duplicate outreach, and dispatches automated notices.
              </p>
            </div>
          </div>

          <Button
            variant="primary"
            size="sm"
            onClick={handleTriggerCadence}
            isLoading={triggerCadence.isPending}
            className="shrink-0 bg-blue-600 hover:bg-blue-500 text-white font-semibold shadow-md shadow-blue-600/25 border border-blue-400/30 px-4 py-2 text-xs rounded-lg transition-all active:scale-[0.98]"
          >
            <Play className="w-3.5 h-3.5 mr-1.5 fill-current" />
            <span>Execute Cadence Run</span>
          </Button>
        </div>
      </div>

      {/* KPI Summary Cards: Solid Glazed Black Boxes */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricsCard
          title="Total Outstanding"
          value={formatCurrency(metrics?.total_receivables || 0)}
          subtitle="All active unpaid balances across ledger accounts"
          icon={DollarSign}
          variant="blue"
          badge="Portfolio"
        />
        <MetricsCard
          title="Total Past-Due"
          value={formatCurrency(metrics?.total_overdue || 0)}
          subtitle="Balances exceeding agreed payment terms"
          icon={AlertCircle}
          variant="coral"
          badge={Number(metrics?.total_overdue || 0) > 0 ? 'Attention' : 'Optimal'}
        />
        <MetricsCard
          title="Days Sales Outstanding"
          value={`${Number(metrics?.dso_days || 0).toFixed(1)} Days`}
          subtitle="Average time to convert sales accounts to cash"
          icon={TrendingDown}
          variant="blue"
          badge="Target < 45d"
        />
        <MetricsCard
          title="Engine Sync As-Of"
          value={metrics?.as_of_date || new Date().toISOString().slice(0, 10)}
          subtitle="Calculated automatically via Celery Beat scheduler"
          icon={Calendar}
          variant="blue"
          badge="Automated"
        />
      </div>

      {/* Inflow Velocity Forecast & Efficiency Arcs Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 xl:col-span-8">
          <InflowVelocityChart />
        </div>
        <div className="lg:col-span-5 xl:col-span-4">
          <CollectionEfficiencyGauge />
        </div>
      </div>

      {/* 5-Bucket Aging Schedule Stratification - Full Width */}
      <AgingChart aging={aging} />

      {/* Autonomous Cadence Matrix & Live Activity Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CadenceHeatmap />
        <RecentActivityList activities={activity} />
      </div>

      {/* Delinquent Attention Queue - High-Priority Invoices */}
      <OverdueList
        invoices={invoices}
        onRecordPayment={onSelectInvoiceForPayment}
        onViewAllInvoices={onNavigateToInvoices}
      />

      {/* Cadence Execution Summary Dialog */}
      <Dialog
        isOpen={!!dispatchResult}
        onClose={() => setDispatchResult(null)}
        title="Cadence Dispatch Execution Summary"
        description="Results from evaluating overdue aging thresholds and dispatching reminder notices"
      >
        {dispatchResult && (
          <div className="space-y-4">
            <div className="p-3.5 rounded-xl bg-[#0f1525] border border-blue-500/30 text-blue-300 text-xs flex items-center gap-2.5">
              <CheckCircle2 className="w-5 h-5 text-blue-400 shrink-0" />
              <span>Cadence run completed successfully. Activity log updated.</span>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3.5 rounded-xl bg-[#08090e] border border-white/[0.08]">
                <div className="text-slate-400">Cadence Rules Evaluated</div>
                <div className="text-base font-bold text-white numeric-mono mt-1">
                  {dispatchResult.evaluated_cadences}
                </div>
              </div>
              <div className="p-3.5 rounded-xl bg-[#08090e] border border-white/[0.08]">
                <div className="text-slate-400">Invoices Scanned</div>
                <div className="text-base font-bold text-white numeric-mono mt-1">
                  {dispatchResult.scanned_invoices}
                </div>
              </div>
              <div className="p-3.5 rounded-xl bg-[#08090e] border border-white/[0.08]">
                <div className="text-blue-400 font-semibold">Reminders Dispatched</div>
                <div className="text-base font-bold text-blue-400 numeric-mono mt-1">
                  {dispatchResult.dispatched_count}
                </div>
              </div>
              <div className="p-3.5 rounded-xl bg-[#08090e] border border-white/[0.08]">
                <div className="text-rose-400 font-semibold">Skipped (Paused by Customer)</div>
                <div className="text-base font-bold text-rose-400 numeric-mono mt-1">
                  {dispatchResult.skipped_paused}
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button variant="primary" size="sm" onClick={() => setDispatchResult(null)}>
                Dismiss
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
};
