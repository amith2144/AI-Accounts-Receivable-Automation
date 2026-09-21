import React, { useState } from 'react';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Invoice, InvoiceStatus } from '@/types';
import { formatCurrency, formatDate } from '@/lib/utils';
import { CreditCard, Ban, FileText, Search } from 'lucide-react';

interface InvoiceTableProps {
  invoices: Invoice[];
  isLoading: boolean;
  onRecordPayment: (invoice: Invoice) => void;
  onVoidInvoice: (invoice: Invoice) => void;
  onSelectInvoiceDetail: (invoice: Invoice) => void;
}

export const InvoiceTable: React.FC<InvoiceTableProps> = ({
  invoices,
  isLoading,
  onRecordPayment,
  onVoidInvoice,
  onSelectInvoiceDetail,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const filtered = invoices.filter((inv) => {
    const matchesSearch =
      inv.invoice_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (inv.customer_name && inv.customer_name.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesStatus =
      statusFilter === 'ALL' || inv.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (status: InvoiceStatus) => {
    switch (status) {
      case 'PAID':
        return <Badge variant="success" dot>Paid</Badge>;
      case 'PARTIALLY_PAID':
        return <Badge variant="warning" dot>Partially Paid</Badge>;
      case 'OVERDUE':
        return <Badge variant="destructive" dot>Overdue</Badge>;
      case 'ISSUED':
        return <Badge variant="default" dot>Issued</Badge>;
      case 'DRAFT':
      case 'PENDING_REVIEW':
        return <Badge variant="neutral" dot>Review</Badge>;
      case 'VOID':
        return <Badge variant="outline">Void</Badge>;
      default:
        return <Badge variant="neutral">{status}</Badge>;
    }
  };

  const statusTabs = [
    { label: 'All Invoices', value: 'ALL' },
    { label: 'Active Issued', value: 'ISSUED' },
    { label: 'Overdue', value: 'OVERDUE' },
    { label: 'Partially Paid', value: 'PARTIALLY_PAID' },
    { label: 'Settled Paid', value: 'PAID' },
    { label: 'Voided', value: 'VOID' },
  ];

  return (
    <div className="space-y-4">
      {/* Control Bar: Search & Status Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {statusTabs.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setStatusFilter(tab.value)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${
                statusFilter === tab.value
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-[#151722] text-slate-400 hover:text-slate-200 hover:bg-[#1e2130]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search invoice number..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full h-8 pl-8 pr-3 rounded-md bg-[#0e1017] border border-[#232634] text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {/* Main Table */}
      <div className="rounded-lg border border-[#232634] bg-[#12131a] overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-3" />
            Loading invoices from ledger...
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            No invoices match the selected filter criteria.
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Invoice #</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Issue Date</TableHead>
                <TableHead>Due Date</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Total Amount</TableHead>
                <TableHead className="text-right">Balance Due</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((inv) => {
                const balance = Number(inv.balance_due);
                const isPayable = balance > 0 && inv.status !== 'VOID';
                const isVoidable = inv.status !== 'VOID' && inv.status !== 'PAID';

                return (
                  <TableRow key={inv.id}>
                    <TableCell className="font-semibold text-white">
                      <button
                        onClick={() => onSelectInvoiceDetail(inv)}
                        className="hover:text-blue-400 transition-colors flex items-center gap-1.5"
                      >
                        <FileText className="w-3.5 h-3.5 text-slate-400" />
                        <span>{inv.invoice_number}</span>
                      </button>
                    </TableCell>
                    <TableCell className="text-xs text-slate-300">
                      {inv.customer_name || inv.customer_id.slice(0, 8)}
                    </TableCell>
                    <TableCell className="text-xs text-slate-400">
                      {formatDate(inv.issue_date)}
                    </TableCell>
                    <TableCell className="text-xs text-slate-400">
                      {formatDate(inv.due_date)}
                    </TableCell>
                    <TableCell>{getStatusBadge(inv.status)}</TableCell>
                    <TableCell className="text-right text-xs text-slate-300 numeric-mono">
                      {formatCurrency(inv.total_amount, inv.currency)}
                    </TableCell>
                    <TableCell className="text-right font-semibold text-white numeric-mono">
                      {formatCurrency(inv.balance_due, inv.currency)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {isPayable && (
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => onRecordPayment(inv)}
                            className="text-xs px-2.5"
                          >
                            <CreditCard className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                            <span>Settle</span>
                          </Button>
                        )}
                        {isVoidable && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onVoidInvoice(inv)}
                            className="text-xs text-slate-400 hover:text-red-400 px-2"
                            title="Void invoice"
                          >
                            <Ban className="w-3.5 h-3.5" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  );
};
