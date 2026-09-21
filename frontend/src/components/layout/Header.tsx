import React, { useEffect, useState } from 'react';
import apiClient from '@/services/api';
import { Button } from '@/components/ui/button';
import {
  Download,
  Upload,
  AlertCircle,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import { PageView } from './Sidebar';

interface HeaderProps {
  currentPage: PageView;
  onOpenUploadModal: () => void;
  isSidebarCollapsed: boolean;
  onToggleSidebar: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentPage,
  onOpenUploadModal,
  isSidebarCollapsed,
  onToggleSidebar,
}) => {
  const [healthStatus, setHealthStatus] = useState<'ok' | 'error' | 'checking'>('checking');
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await apiClient.get('/health');
        if (res.status === 200) setHealthStatus('ok');
        else setHealthStatus('error');
      } catch {
        setHealthStatus('error');
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const titles: Record<PageView, { title: string; subtitle: string; tag: string }> = {
    dashboard: {
      title: 'Operational Executive Dashboard',
      subtitle: 'Real-time aging analytics, overdue receivables, and collection performance',
      tag: 'Analytics',
    },
    invoices: {
      title: 'Invoice Ledger & Ingestion',
      subtitle: 'Review accounts, upload PDF/image invoices, and verify OCR extractions',
      tag: 'Ledger',
    },
    customers: {
      title: 'Debtor Directory & Ledger',
      subtitle: 'Manage customer credit terms, contact directories, and cadence overrides',
      tag: 'Accounts',
    },
    cadences: {
      title: 'Reminder Cadences & Audit Feed',
      subtitle: 'Configure automated aging outreach thresholds and review immutable logs',
      tag: 'Automations',
    },
  };

  const handleExportCsv = async () => {
    setIsExporting(true);
    try {
      const response = await apiClient.get('/integrations/accounting/export?export_type=reconciliation&format=csv', {
        responseType: 'blob',
      });
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ar_reconciliation_ledger_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch {
      alert('Failed to generate CSV reconciliation export. Ensure you are authorized.');
    } finally {
      setIsExporting(false);
    }
  };

  const { title, subtitle, tag } = titles[currentPage];

  return (
    <header className="h-16 border-b border-white/[0.06] bg-[#07080c] px-5 sm:px-6 flex items-center justify-between shrink-0 z-20 relative">
      <div className="flex items-center gap-3.5 min-w-0">
        {/* Toggle Sidebar Button */}
        <button
          onClick={onToggleSidebar}
          title={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.05] transition-colors shrink-0"
        >
          {isSidebarCollapsed ? (
            <PanelLeftOpen className="w-4 h-4 text-slate-300 hover:text-blue-400 transition-colors" />
          ) : (
            <PanelLeftClose className="w-4 h-4 text-slate-400 hover:text-slate-200 transition-colors" />
          )}
        </button>

        <div className="h-5 w-px bg-white/[0.06] shrink-0" />

        <div className="truncate">
          <div className="flex items-center gap-2">
            <h1 className="text-sm sm:text-base font-semibold text-white tracking-tight truncate">
              {title}
            </h1>
            <span className="hidden sm:inline-block px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-500/15 text-blue-300 border border-blue-500/25">
              {tag}
            </span>
          </div>
          <p className="text-[11px] sm:text-xs text-slate-400 truncate hidden md:block">
            {subtitle}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2.5 sm:gap-3 shrink-0">
        {/* Backend API Health Status */}
        <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-white/[0.06] bg-[#0d0f17] text-xs shadow-inner">
          {healthStatus === 'ok' ? (
            <>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
              </span>
              <span className="text-slate-300 text-[11px] font-medium">Gateway Online</span>
            </>
          ) : healthStatus === 'checking' ? (
            <>
              <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
              <span className="text-slate-400 text-[11px]">Connecting...</span>
            </>
          ) : (
            <>
              <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
              <span className="text-rose-400 text-[11px] font-medium">API Offline</span>
            </>
          )}
        </div>

        {/* Quick CSV Export */}
        <Button
          variant="secondary"
          size="sm"
          onClick={handleExportCsv}
          isLoading={isExporting}
          className="text-xs bg-[#10121c] hover:bg-[#181b2c] border-white/[0.07] text-slate-300 hover:text-white"
        >
          <Download className="w-3.5 h-3.5 mr-1" />
          <span className="hidden sm:inline">Export Ledger</span>
          <span className="sm:hidden">Export</span>
        </Button>

        {/* Quick Upload Action */}
        <Button
          variant="primary"
          size="sm"
          onClick={onOpenUploadModal}
          className="text-xs bg-blue-600 hover:bg-blue-500 text-white border border-blue-400/30 shadow-md shadow-blue-600/25"
        >
          <Upload className="w-3.5 h-3.5 mr-1" />
          <span className="hidden sm:inline">Upload Invoice</span>
          <span className="sm:hidden">Upload</span>
        </Button>
      </div>
    </header>
  );
};
