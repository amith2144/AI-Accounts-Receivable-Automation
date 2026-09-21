import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CollectionActivity, ActivityType } from '@/types';
import { formatDate } from '@/lib/utils';
import { History, Mail, CreditCard, CheckCircle2, FileText, Bot, Filter } from 'lucide-react';

interface ActivityTimelineProps {
  activities: CollectionActivity[];
  isLoading: boolean;
}

export const ActivityTimeline: React.FC<ActivityTimelineProps> = ({
  activities,
  isLoading,
}) => {
  const [filterType, setFilterType] = useState<string>('ALL');

  const filtered = activities.filter((act) => {
    if (filterType === 'ALL') return true;
    return act.activity_type === filterType;
  });

  const getActivityIcon = (type: ActivityType) => {
    switch (type) {
      case 'REMINDER_SENT':
        return <Mail className="w-4 h-4 text-blue-400" />;
      case 'PAYMENT_APPLIED':
        return <CreditCard className="w-4 h-4 text-emerald-400" />;
      case 'STATUS_CHANGE':
        return <CheckCircle2 className="w-4 h-4 text-purple-400" />;
      default:
        return <FileText className="w-4 h-4 text-slate-400" />;
    }
  };

  const getBadgeVariant = (type: ActivityType) => {
    switch (type) {
      case 'REMINDER_SENT':
        return 'default';
      case 'PAYMENT_APPLIED':
        return 'success';
      case 'STATUS_CHANGE':
        return 'secondary';
      default:
        return 'neutral';
    }
  };

  return (
    <Card className="glass-card">
      <CardHeader className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 gap-3">
        <div>
          <CardTitle className="text-base flex items-center gap-2">
            <History className="w-4 h-4 text-blue-400" />
            <span>Immutable Collection Activity Audit Feed</span>
          </CardTitle>
          <CardDescription>
            Legally accountable and auditable record of all collection touchpoints and payments
          </CardDescription>
        </div>

        {/* Filter Dropdown */}
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="h-8 rounded-md bg-[#0e1017] border border-[#232634] text-xs text-white px-2.5 focus:outline-none focus:border-blue-500"
          >
            <option value="ALL">All Activities</option>
            <option value="REMINDER_SENT">Reminders Dispatched</option>
            <option value="PAYMENT_APPLIED">Payments Applied</option>
            <option value="STATUS_CHANGE">Status Changes</option>
            <option value="MANUAL_NOTE">Manual Notes</option>
          </select>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-3" />
            Loading activity stream...
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            No activity records match the selected filter.
          </div>
        ) : (
          <div className="divide-y divide-[#1e212f]">
            {filtered.map((act) => (
              <div key={act.id} className="p-4 flex items-start justify-between hover:bg-[#151722] transition-colors">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-[#1a1c27] border border-[#272b3c] shrink-0 mt-0.5">
                    {getActivityIcon(act.activity_type)}
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant={getBadgeVariant(act.activity_type)}>
                        {act.activity_type.replace(/_/g, ' ')}
                      </Badge>
                      {act.performed_by === 'SYSTEM_AUTOMATION' ? (
                        <span className="px-1.5 py-0.2 rounded text-[10px] bg-blue-950/60 text-blue-400 border border-blue-800/40 flex items-center gap-1 font-medium">
                          <Bot className="w-3 h-3" /> AI Automation
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">by {act.performed_by}</span>
                      )}
                    </div>

                    <div className="text-xs text-slate-300">
                      {act.details?.recipient_email && (
                        <span>Outreach dispatched to <strong className="text-white">{act.details.recipient_email}</strong></span>
                      )}
                      {act.details?.amount && (
                        <span>Settlement payment of <strong className="text-emerald-400">${act.details.amount}</strong> applied</span>
                      )}
                      {act.details?.status && (
                        <span>Status updated to <strong className="text-white">{act.details.status}</strong></span>
                      )}
                    </div>

                    {act.details?.subject && (
                      <div className="text-[11px] text-slate-500 italic">
                        Subject: "{act.details.subject}"
                      </div>
                    )}
                  </div>
                </div>

                <div className="text-[11px] text-slate-500 numeric-mono shrink-0 ml-4">
                  {formatDate(act.created_at)}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
