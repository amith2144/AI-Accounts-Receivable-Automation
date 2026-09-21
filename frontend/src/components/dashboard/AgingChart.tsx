import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { AgingDistribution } from '@/types';
import { formatCurrency } from '@/lib/utils';
import { Clock, Layers } from 'lucide-react';

interface AgingChartProps {
  aging: AgingDistribution | undefined;
}

export const AgingChart: React.FC<AgingChartProps> = ({ aging }) => {
  const buckets = [
    {
      key: 'CURRENT',
      label: 'Current (Not Due)',
      sub: 'Within terms',
      gradient: 'from-slate-700 to-slate-600',
      barColor: 'bg-slate-600',
      text: 'text-slate-200',
      border: 'border-white/[0.08]',
      dot: 'bg-slate-400',
      isHighlight: false,
    },
    {
      key: 'DAYS_1_30',
      label: '1–30 Days',
      sub: 'Early stage',
      gradient: 'from-blue-600 to-blue-500',
      barColor: 'bg-blue-500',
      text: 'text-blue-400',
      border: 'border-blue-500/25',
      dot: 'bg-blue-400',
      isHighlight: false,
    },
    {
      key: 'DAYS_31_60',
      label: '31–60 Days',
      sub: 'Moderate overdue',
      gradient: 'from-blue-700 to-blue-600',
      barColor: 'bg-blue-600',
      text: 'text-blue-300',
      border: 'border-blue-600/20',
      dot: 'bg-blue-500',
      isHighlight: false,
    },
    {
      key: 'DAYS_61_90',
      label: '61–90 Days',
      sub: 'Escalated outreach',
      gradient: 'from-blue-800 to-blue-700',
      barColor: 'bg-blue-700',
      text: 'text-blue-200',
      border: 'border-blue-700/20',
      dot: 'bg-indigo-400',
      isHighlight: false,
    },
    {
      key: 'DAYS_90_PLUS',
      label: '90+ Days Critical',
      sub: 'Impairment risk',
      gradient: 'from-rose-600 to-rose-500',
      barColor: 'bg-rose-500',
      text: 'text-rose-400',
      border: 'border-rose-500/30',
      dot: 'bg-rose-500',
      isHighlight: true,
    },
  ];

  const totalReceivables = Number(aging?.total_receivables || 0);

  return (
    <Card className="piano-black-card rounded-2xl relative overflow-hidden">
      <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 gap-3 border-b border-white/[0.06]">
        <div>
          <div className="flex items-center gap-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-400" />
              <span>Aging Schedule Stratification</span>
            </CardTitle>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-blue-500/15 text-blue-300 border border-blue-500/25 flex items-center gap-1">
              <Layers className="w-2.5 h-2.5" /> 5-Bucket Engine
            </span>
          </div>
          <CardDescription className="text-xs text-slate-400 mt-1">
            Autonomous portfolio aging breakdown by customer payment terms
          </CardDescription>
        </div>

        <div className="text-left sm:text-right">
          <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
            Total Invoiced Active
          </div>
          <div className="text-xl font-bold text-white numeric-mono">
            {formatCurrency(totalReceivables)}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6 pt-5">
        {/* Recessed Metallic Track */}
        <div className="space-y-2">
          <div className="h-3 w-full rounded-full metallic-groove flex overflow-hidden p-0.5">
            {totalReceivables === 0 ? (
              <div className="w-full h-full rounded-full bg-slate-900/60 flex items-center justify-center text-[9px] text-slate-500">
                No active outstanding ledger balances
              </div>
            ) : (
              buckets.map((b) => {
                const bucketData = aging?.buckets[b.key];
                const balance = Number(bucketData?.total_balance || 0);
                const percentage = totalReceivables > 0 ? (balance / totalReceivables) * 100 : 0;
                if (percentage <= 0) return null;

                return (
                  <div
                    key={b.key}
                    title={`${b.label}: ${formatCurrency(balance)} (${percentage.toFixed(1)}%)`}
                    className={`bg-gradient-to-r ${b.gradient} h-full transition-all duration-300 first:rounded-l-full last:rounded-r-full hover:brightness-110 cursor-pointer`}
                    style={{ width: `${percentage}%` }}
                  />
                );
              })
            )}
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
            <span>Portfolio Stratification</span>
            <span>{totalReceivables > 0 ? '100% of accounts evaluated' : 'Standby'}</span>
          </div>
        </div>

        {/* 5 Solid Glazed Sub-Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {buckets.map((b) => {
            const bucketData = aging?.buckets[b.key];
            const balance = Number(bucketData?.total_balance || 0);
            const count = bucketData?.invoice_count || 0;
            const percentage = totalReceivables > 0 ? (balance / totalReceivables) * 100 : 0;

            return (
              <div
                key={b.key}
                className={`p-3 sm:p-3.5 rounded-xl piano-black-subcard flex flex-col justify-between space-y-2.5 min-w-0 ${b.border} ${
                  b.isHighlight ? 'hover:border-rose-500/50' : 'hover:border-blue-500/40'
                }`}
              >
                <div className="min-w-0">
                  <div className="flex items-center justify-between gap-1.5 min-w-0">
                    <span className="text-xs font-semibold text-slate-200 truncate" title={b.label}>
                      {b.label}
                    </span>
                    <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${b.dot}`} />
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5 truncate" title={b.sub}>
                    {b.sub}
                  </div>

                  <div
                    className={`text-base sm:text-lg font-bold ${b.text} numeric-mono mt-1.5 tracking-tight truncate`}
                    title={formatCurrency(balance)}
                  >
                    {formatCurrency(balance)}
                  </div>
                </div>

                {/* Sub-bar for this bucket */}
                <div className="space-y-1 pt-2 border-t border-white/[0.05]">
                  <div className="h-1 w-full bg-[#050609] rounded-full overflow-hidden">
                    <div
                      className={`h-full ${b.barColor} transition-all duration-500`}
                      style={{ width: `${Math.min(percentage, 100)}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-slate-400">
                    <span>{count} invoice{count !== 1 ? 's' : ''}</span>
                    <span className="font-semibold text-slate-300">{percentage.toFixed(1)}%</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
};
