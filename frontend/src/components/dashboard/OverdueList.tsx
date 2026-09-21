import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Invoice } from '@/types';
import { formatCurrency, formatDate } from '@/lib/utils';
import { AlertTriangle, CreditCard, ArrowUpRight, CheckCircle2 } from 'lucide-react';

interface OverdueListProps {
  invoices: Invoice[];
  onRecordPayment: (invoice: Invoice) => void;
  onViewAllInvoices: () => void;
}

export const OverdueList: React.FC<OverdueListProps> = ({
  invoices,
  onRecordPayment,
  onViewAllInvoices,
}) => {
  const overdueInvoices = invoices
    .filter((inv) => inv.status === 'OVERDUE' || Number(inv.balance_due) > 0)
    .slice(0, 5);

  return (
    <Card className="piano-black-card rounded-2xl relative overflow-hidden flex flex-col justify-between">
      <div>
        <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-white/[0.06]">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-[#180f14] text-rose-400 border border-rose-500/25">
                <AlertTriangle className="w-4 h-4" />
              </div>
              <span>Delinquent Attention Queue</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-400 mt-1">
              High-priority invoices exceeding agreed customer payment terms
            </CardDescription>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onViewAllInvoices}
            className="text-xs text-blue-400 hover:text-blue-300 hover:bg-blue-500/10"
          >
            <span>View All Invoices</span>
            <ArrowUpRight className="w-3.5 h-3.5 ml-1" />
          </Button>
        </CardHeader>

        <CardContent className="p-0">
          {overdueInvoices.length === 0 ? (
            <div className="p-10 text-center space-y-2">
              <div className="w-10 h-10 rounded-full bg-[#0e1220] border border-blue-500/25 text-blue-400 flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div className="text-xs font-semibold text-slate-200">No Delinquent Receivables</div>
              <p className="text-[11px] text-slate-400 max-w-xs mx-auto">
                All accounts are current within agreed payment terms. Working capital health is optimal.
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-white/[0.05] hover:bg-transparent">
                  <TableHead className="text-slate-400 text-[11px]">Invoice #</TableHead>
                  <TableHead className="text-slate-400 text-[11px]">Due Date</TableHead>
                  <TableHead className="text-slate-400 text-[11px]">Status</TableHead>
                  <TableHead className="text-right text-slate-400 text-[11px]">Balance Due</TableHead>
                  <TableHead className="text-right text-slate-400 text-[11px]">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {overdueInvoices.map((inv) => (
                  <TableRow
                    key={inv.id}
                    className="border-white/[0.04] hover:bg-white/[0.02] transition-colors group"
                  >
                    <TableCell className="font-semibold text-white text-xs">
                      <span className="font-mono bg-[#07080c] px-2 py-0.5 rounded border border-white/[0.08] text-slate-200">
                        {inv.invoice_number}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-slate-400">
                      {formatDate(inv.due_date)}
                    </TableCell>
                    <TableCell>
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/25 inline-flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                        {inv.status}
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-semibold text-white numeric-mono text-xs">
                      {formatCurrency(inv.balance_due, inv.currency)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => onRecordPayment(inv)}
                        className="text-xs h-7 px-3 bg-[#0d1220] hover:bg-blue-600 hover:text-white text-blue-300 border-blue-500/30 transition-all shadow-sm"
                      >
                        <CreditCard className="w-3 h-3 mr-1 text-blue-400 group-hover:text-white" />
                        <span>Settle</span>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </div>
    </Card>
  );
};
