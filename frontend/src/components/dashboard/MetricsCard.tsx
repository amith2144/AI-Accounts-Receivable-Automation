import React from 'react';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { LucideIcon } from 'lucide-react';

interface MetricsCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: LucideIcon;
  variant?: 'blue' | 'coral';
  badge?: string;
}

export const MetricsCard: React.FC<MetricsCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = 'blue',
  badge,
}) => {
  const isCoral = variant === 'coral';

  return (
    <Card
      className={cn(
        'p-5 piano-black-card rounded-xl relative overflow-hidden group',
        isCoral && 'hover:border-rose-500/30'
      )}
    >
      <div className="flex items-start justify-between relative z-10">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <p className="text-[10px] font-semibold text-slate-400 tracking-wider uppercase">
              {title}
            </p>
            {badge && (
              <span
                className={cn(
                  'px-1.5 py-0.2 rounded text-[10px] font-medium border select-none',
                  isCoral
                    ? 'bg-rose-500/10 text-rose-400 border-rose-500/25'
                    : 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                )}
              >
                {badge}
              </span>
            )}
          </div>
          <div className="text-2xl font-bold tracking-tight text-white numeric-mono">
            {value}
          </div>
          {subtitle && (
            <p className="text-[11px] text-slate-400/90 leading-snug">{subtitle}</p>
          )}
        </div>

        <div
          className={cn(
            'p-2.5 rounded-xl border flex items-center justify-center transition-colors shadow-inner',
            isCoral
              ? 'bg-[#150e13] border-rose-500/20 text-rose-400'
              : 'bg-[#10121b] border-white/[0.08] text-blue-400'
          )}
        >
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </Card>
  );
};
