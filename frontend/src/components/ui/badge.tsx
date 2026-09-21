import React from 'react';
import { cn } from '@/lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'success' | 'warning' | 'destructive' | 'outline' | 'neutral';
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = 'default',
  dot = false,
  children,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors select-none';

  const variants = {
    default: 'bg-blue-950/60 text-blue-300 border border-blue-800/40',
    secondary: 'bg-[#1e2130] text-slate-300 border border-[#2d3248]',
    success: 'bg-emerald-950/60 text-emerald-300 border border-emerald-800/40',
    warning: 'bg-amber-950/60 text-amber-300 border border-amber-800/40',
    destructive: 'bg-red-950/60 text-red-300 border border-red-800/40',
    outline: 'border border-[#232634] text-slate-300 bg-transparent',
    neutral: 'bg-slate-800/70 text-slate-300 border border-slate-700/50',
  };

  const dotColors = {
    default: 'bg-blue-400',
    secondary: 'bg-slate-400',
    success: 'bg-emerald-400',
    warning: 'bg-amber-400',
    destructive: 'bg-red-400',
    outline: 'bg-slate-400',
    neutral: 'bg-slate-400',
  };

  return (
    <div className={cn(baseStyles, variants[variant], className)} {...props}>
      {dot && (
        <span className={cn('w-1.5 h-1.5 rounded-full mr-1.5 animate-pulse', dotColors[variant])} />
      )}
      {children}
    </div>
  );
};
