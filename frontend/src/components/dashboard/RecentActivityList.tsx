import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { CollectionActivity } from '@/types';
import { formatDate } from '@/lib/utils';
import { History, Mail, CreditCard, FileText, CheckCircle2, Bot, Radio } from 'lucide-react';

interface RecentActivityListProps {
  activities: CollectionActivity[];
}

export const RecentActivityList: React.FC<RecentActivityListProps> = ({ activities }) => {
  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'REMINDER_SENT':
        return <Mail className="w-4 h-4 text-blue-400" />;
      case 'PAYMENT_APPLIED':
        return <CreditCard className="w-4 h-4 text-blue-300" />;
      case 'STATUS_CHANGE':
        return <CheckCircle2 className="w-4 h-4 text-blue-400" />;
      default:
        return <FileText className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <Card className="piano-black-card rounded-2xl relative overflow-hidden flex flex-col justify-between">
      <div>
        <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-white/[0.06]">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
                <History className="w-4 h-4" />
              </div>
              <span>Recent Activity Stream</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-400 mt-1">
              Immutable operational touchpoints, automated reminder dispatches, and settlements
            </CardDescription>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#0c101c] border border-blue-500/25 text-[10px] font-medium text-blue-400">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
            <span>Audit Live</span>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {activities.length === 0 ? (
            <div className="p-8 text-center space-y-3">
              <div className="w-11 h-11 rounded-2xl bg-[#080a11] border border-white/[0.08] flex items-center justify-center mx-auto shadow-inner text-blue-400">
                <Radio className="w-5 h-5 animate-pulse text-blue-400" />
              </div>
              <div className="space-y-1">
                <div className="text-xs font-semibold text-slate-200">Audit Stream Standby</div>
                <p className="text-[11px] text-slate-400 max-w-sm mx-auto leading-relaxed">
                  Autonomous cadence dispatches, email outreach touchpoints, and settlement entries will stream here chronologically as jobs run.
                </p>
              </div>
              <div className="inline-flex items-center gap-1.5 text-[10px] text-slate-500 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                Listening for Celery Beat & API worker events
              </div>
            </div>
          ) : (
            <div className="divide-y divide-white/[0.04]">
              {activities.slice(0, 6).map((act) => (
                <div
                  key={act.id}
                  className="p-3.5 sm:p-4 flex items-center justify-between hover:bg-white/[0.02] transition-colors group"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="p-2 rounded-xl bg-[#0c0e18] border border-white/[0.08] shrink-0 group-hover:border-blue-500/30 transition-colors">
                      {getActivityIcon(act.activity_type)}
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-semibold text-white flex items-center gap-2">
                        <span className="truncate">{act.activity_type.replace(/_/g, ' ')}</span>
                        {act.performed_by === 'SYSTEM_AUTOMATION' && (
                          <span className="px-1.5 py-0.2 rounded text-[9px] bg-blue-500/15 text-blue-400 border border-blue-500/30 flex items-center gap-0.5 shrink-0">
                            <Bot className="w-2.5 h-2.5" /> AI Auto
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-0.5 truncate">
                        {act.details?.recipient_email
                          ? `Dispatched to ${act.details.recipient_email}`
                          : act.details?.amount
                          ? `Settlement of $${act.details.amount} recorded`
                          : `Invoice ${act.invoice_id ? act.invoice_id.slice(0, 8) : ''}`}
                      </div>
                    </div>
                  </div>
                  <div className="text-[11px] text-slate-500 numeric-mono shrink-0 ml-3">
                    {formatDate(act.created_at)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </div>
    </Card>
  );
};
