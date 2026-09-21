import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { cadenceService } from '@/services/cadenceService';
import { CadenceRuleEditor } from '@/components/cadences/CadenceRuleEditor';
import { ActivityTimeline } from '@/components/cadences/ActivityTimeline';
import { Button } from '@/components/ui/button';
import { Dialog } from '@/components/ui/dialog';
import { ReminderCadence } from '@/types';
import { Play, Clock, History, CheckCircle2 } from 'lucide-react';

export const CadencesPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'rules' | 'activities'>('rules');
  const [dispatchResult, setDispatchResult] = useState<any | null>(null);

  const cadencesQuery = useQuery({
    queryKey: ['cadences'],
    queryFn: () => cadenceService.getCadences(),
  });

  const activitiesQuery = useQuery({
    queryKey: ['activities'],
    queryFn: () => cadenceService.getActivities({ limit: 50 }),
  });

  const triggerMutation = useMutation({
    mutationFn: () => cadenceService.triggerRun(),
    onSuccess: (res) => {
      setDispatchResult(res);
      queryClient.invalidateQueries({ queryKey: ['activities'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
    },
  });

  const saveCadenceMutation = useMutation({
    mutationFn: (cadence: ReminderCadence) =>
      cadenceService.updateCadence(cadence.id, cadence),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cadences'] });
    },
  });

  const handleSaveRule = async (c: ReminderCadence) => {
    try {
      await saveCadenceMutation.mutateAsync(c);
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to update cadence rule.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white tracking-tight">
            Automated Outreach Cadences & Audit
          </h2>
          <p className="text-xs text-slate-400">
            Configure time-decayed reminder rules, tone templates, and inspect the immutable communication log
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={() => triggerMutation.mutate()}
            isLoading={triggerMutation.isPending}
            className="text-xs"
          >
            <Play className="w-3.5 h-3.5 mr-1.5 fill-current" />
            <span>Execute Manual Run</span>
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-[#1e212f] pb-3">
        <button
          onClick={() => setActiveTab('rules')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-md text-xs font-medium transition-colors ${
            activeTab === 'rules'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'bg-[#151722] text-slate-400 hover:text-slate-200 hover:bg-[#1e2130]'
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          <span>Cadence Rule Configurations</span>
        </button>

        <button
          onClick={() => setActiveTab('activities')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-md text-xs font-medium transition-colors ${
            activeTab === 'activities'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'bg-[#151722] text-slate-400 hover:text-slate-200 hover:bg-[#1e2130]'
          }`}
        >
          <History className="w-3.5 h-3.5" />
          <span>Activity Audit Trail Feed</span>
        </button>
      </div>

      {/* Content */}
      {activeTab === 'rules' ? (
        <CadenceRuleEditor
          cadences={cadencesQuery.data || []}
          onSaveRule={handleSaveRule}
        />
      ) : (
        <ActivityTimeline
          activities={activitiesQuery.data?.items || []}
          isLoading={activitiesQuery.isLoading}
        />
      )}

      {/* Manual Dispatch Feedback Dialog */}
      <Dialog
        isOpen={!!dispatchResult}
        onClose={() => setDispatchResult(null)}
        title="Cadence Dispatch Execution Summary"
        description="Results from evaluating overdue aging thresholds and dispatching reminder notices"
      >
        {dispatchResult && (
          <div className="space-y-4">
            <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800/40 text-emerald-300 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Cadence run completed. Emails rendered and activity feed updated.</span>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-md bg-[#0e1017] border border-[#232634]">
                <div className="text-slate-400">Cadence Rules Evaluated</div>
                <div className="text-base font-bold text-white numeric-mono mt-1">
                  {dispatchResult.evaluated_cadences}
                </div>
              </div>
              <div className="p-3 rounded-md bg-[#0e1017] border border-[#232634]">
                <div className="text-slate-400">Invoices Scanned</div>
                <div className="text-base font-bold text-white numeric-mono mt-1">
                  {dispatchResult.scanned_invoices}
                </div>
              </div>
              <div className="p-3 rounded-md bg-[#0e1017] border border-[#232634]">
                <div className="text-emerald-400 font-semibold">Reminders Dispatched</div>
                <div className="text-base font-bold text-emerald-400 numeric-mono mt-1">
                  {dispatchResult.dispatched_count}
                </div>
              </div>
              <div className="p-3 rounded-md bg-[#0e1017] border border-[#232634]">
                <div className="text-amber-400 font-semibold">Skipped (Paused by Debtor)</div>
                <div className="text-base font-bold text-amber-400 numeric-mono mt-1">
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
