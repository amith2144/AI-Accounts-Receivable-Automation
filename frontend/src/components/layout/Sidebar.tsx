import React from 'react';
import { useAuth } from '@/context/AuthContext';
import {
  LayoutDashboard,
  Receipt,
  Users,
  Clock,
  LogOut,
  Sparkles,
  ShieldAlert,
  ShieldCheck,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export type PageView = 'dashboard' | 'invoices' | 'customers' | 'cadences';

export interface SidebarProps {
  currentPage: PageView;
  onSelectPage: (page: PageView) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onSelectPage,
  isCollapsed,
  onToggleCollapse,
}) => {
  const { user, logout } = useAuth();

  const navItems = [
    {
      id: 'dashboard' as PageView,
      label: 'Operational Dashboard',
      icon: LayoutDashboard,
      description: 'KPIs, DSO & Aging Buckets',
    },
    {
      id: 'invoices' as PageView,
      label: 'Invoice Management',
      icon: Receipt,
      description: 'Ledger & AI OCR Verification',
    },
    {
      id: 'customers' as PageView,
      label: 'Customer Directory',
      icon: Users,
      description: 'Terms & Reminder Overrides',
    },
    {
      id: 'cadences' as PageView,
      label: 'Cadence Automations',
      icon: Clock,
      description: 'Outreach Rules & Audit Feed',
    },
  ];

  return (
    <aside
      className={cn(
        'border-r border-white/[0.045] bg-[#07080c]/98 backdrop-blur-2xl flex flex-col h-screen select-none shrink-0 transition-all duration-300 ease-in-out z-30 relative',
        isCollapsed ? 'w-[72px]' : 'w-64'
      )}
    >
      {/* Brand Header */}
      <div
        className={cn(
          'border-b border-white/[0.045] flex items-center transition-all',
          isCollapsed ? 'p-3 flex-col gap-2 justify-center' : 'p-4 justify-between'
        )}
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-b from-blue-500 to-blue-700 flex items-center justify-center text-white font-bold shadow-lg shadow-blue-600/25 shrink-0 border border-blue-400/20">
            <Receipt className="w-4.5 h-4.5 text-white" />
          </div>

          {!isCollapsed && (
            <div className="overflow-hidden transition-opacity duration-200">
              <div className="text-sm font-semibold text-white tracking-tight flex items-center gap-1.5">
                <span>AR Control</span>
                <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">
                  AI
                </span>
              </div>
              <div className="text-[11px] text-slate-400">Autonomous Receivables</div>
            </div>
          )}
        </div>

        {/* Sidebar Toggle Button */}
        <button
          onClick={onToggleCollapse}
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className={cn(
            'p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.05] transition-colors',
            isCollapsed && 'w-8 h-8 flex items-center justify-center'
          )}
        >
          {isCollapsed ? (
            <PanelLeftOpen className="w-4 h-4 text-slate-300 hover:text-blue-400 transition-colors" />
          ) : (
            <PanelLeftClose className="w-4 h-4 text-slate-400 hover:text-slate-200 transition-colors" />
          )}
        </button>
      </div>

      {/* Navigation Links */}
      <div
        className={cn(
          'flex-1 px-2.5 py-4 space-y-1.5',
          isCollapsed ? 'overflow-visible' : 'overflow-y-auto overflow-x-hidden'
        )}
      >
        {!isCollapsed && (
          <div className="px-2.5 pb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            Navigation
          </div>
        )}

        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentPage === item.id;

          return (
            <div key={item.id} className="relative group flex justify-center">
              <button
                onClick={() => onSelectPage(item.id)}
                title={isCollapsed ? `${item.label} — ${item.description}` : undefined}
                className={cn(
                  'w-full flex items-center rounded-lg text-xs font-medium transition-all group text-left relative',
                  isCollapsed
                    ? 'h-11 w-11 justify-center p-0'
                    : 'px-3 py-2.5 justify-between',
                  isActive
                    ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30 shadow-sm shadow-blue-500/10'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                )}
              >
                {/* Active left indicator bar for collapsed mode */}
                {isActive && isCollapsed && (
                  <span className="absolute -left-1.5 top-1/2 -translate-y-1/2 w-1.5 h-6 bg-blue-500 rounded-r-full shadow-md shadow-blue-500/60" />
                )}

                <div className={cn('flex items-center gap-3', isCollapsed ? 'justify-center' : 'truncate')}>
                  <Icon
                    className={cn(
                      'w-4 h-4 transition-colors shrink-0',
                      isActive ? 'text-blue-400' : 'text-slate-400 group-hover:text-slate-200'
                    )}
                  />
                  {!isCollapsed && (
                    <div className="truncate">
                      <div className={cn('leading-tight', isActive ? 'font-semibold text-white' : 'text-slate-300')}>
                        {item.label}
                      </div>
                      <div className="text-[10px] text-slate-400 truncate">{item.description}</div>
                    </div>
                  )}
                </div>

                {!isCollapsed && isActive && (
                  <ChevronRight className="w-3.5 h-3.5 text-blue-400 shrink-0 ml-2" />
                )}
              </button>

              {/* Floating Tooltip in Collapsed Mode */}
              {isCollapsed && (
                <div className="absolute left-[calc(100%+10px)] top-1/2 -translate-y-1/2 px-3 py-2 rounded-xl bg-[#11131e] border border-white/[0.12] shadow-2xl shadow-black/90 whitespace-nowrap z-50 pointer-events-none transition-all duration-200 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0">
                  <div className="text-xs font-semibold text-white tracking-tight">{item.label}</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">{item.description}</div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* AI Automation Status (Charcoal & Sapphire) */}
      <div className="px-2.5 pb-3">
        {isCollapsed ? (
          <div className="group relative flex justify-center">
            <div className="w-10 h-10 rounded-xl bg-[#0c0e17] border border-blue-500/25 flex items-center justify-center cursor-default">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500" />
              </span>
            </div>
            <div className="absolute left-[calc(100%+10px)] top-1/2 -translate-y-1/2 px-3 py-2 rounded-xl bg-[#11131e] border border-blue-500/30 shadow-2xl z-50 whitespace-nowrap opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-200 pointer-events-none">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-400">
                <Sparkles className="w-3.5 h-3.5" />
                Aging Engine: Active
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5">Celery Beat batch runner connected</div>
            </div>
          </div>
        ) : (
          <div className="p-3 rounded-xl bg-[#0c0e17] border border-white/[0.05] shadow-sm relative overflow-hidden">
            <div className="flex items-center justify-between text-[11px] mb-1">
              <span className="text-slate-300 font-medium flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                Aging Engine
              </span>
              <span className="inline-flex items-center gap-1 text-blue-400 font-medium text-[10px] px-1.5 py-0.5 rounded bg-blue-950/40 border border-blue-800/40">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                ACTIVE
              </span>
            </div>
            <div className="text-[10px] text-slate-400 leading-relaxed">
              Automated 5-bucket calculation active with Celery Beat scheduler.
            </div>
          </div>
        )}
      </div>

      {/* User Profile & Sign Out */}
      <div className="p-2.5 border-t border-white/[0.045] bg-[#050609]">
        {isCollapsed ? (
          <div className="flex flex-col items-center gap-2">
            <div className="group relative">
              <div className="w-9 h-9 rounded-xl bg-[#12141e] border border-white/[0.08] flex items-center justify-center text-xs font-bold text-slate-200">
                {user?.username?.charAt(0).toUpperCase() || 'U'}
              </div>
              <div className="absolute left-[calc(100%+10px)] top-1/2 -translate-y-1/2 px-3 py-1.5 rounded-xl bg-[#11131e] border border-white/[0.12] shadow-2xl z-50 whitespace-nowrap opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-200 pointer-events-none">
                <div className="text-xs font-semibold text-white">{user?.username}</div>
                <div className="text-[10px] text-slate-400">{user?.role}</div>
              </div>
            </div>

            <button
              onClick={logout}
              title="Sign out"
              className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-rose-400 hover:bg-rose-950/20 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 truncate">
              <div className="w-8 h-8 rounded-xl bg-[#12141e] border border-white/[0.08] flex items-center justify-center text-xs font-bold text-slate-200 shrink-0">
                {user?.username?.charAt(0).toUpperCase() || 'U'}
              </div>
              <div className="truncate">
                <div className="text-xs font-semibold text-slate-200 truncate">{user?.username}</div>
                <div className="text-[10px] text-slate-400 flex items-center gap-1">
                  {user?.role === 'ADMIN' ? (
                    <span className="text-blue-300 flex items-center gap-0.5 font-medium">
                      <ShieldCheck className="w-3 h-3" /> Admin
                    </span>
                  ) : (
                    <span className="text-slate-400 flex items-center gap-0.5 font-medium">
                      <ShieldAlert className="w-3 h-3" /> Operator
                    </span>
                  )}
                </div>
              </div>
            </div>
            <button
              onClick={logout}
              title="Sign out"
              className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-950/20 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </aside>
  );
};
