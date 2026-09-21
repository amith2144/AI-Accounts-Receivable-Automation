import React from 'react';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Customer } from '@/types';
import { formatCurrency } from '@/lib/utils';
import { Mail, Phone, Bell, BellOff } from 'lucide-react';

interface CustomerListProps {
  customers: Customer[];
  isLoading: boolean;
  onToggleReminder: (customer: Customer) => void;
}

export const CustomerList: React.FC<CustomerListProps> = ({
  customers,
  isLoading,
  onToggleReminder,
}) => {
  return (
    <div className="rounded-lg border border-[#232634] bg-[#12131a] overflow-hidden">
      {isLoading ? (
        <div className="p-12 text-center text-slate-400 text-sm">
          <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-3" />
          Loading customers directory...
        </div>
      ) : customers.length === 0 ? (
        <div className="p-12 text-center text-slate-500 text-sm">
          No customer accounts found in ledger directory.
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Customer / Business Name</TableHead>
              <TableHead>Remittance Email</TableHead>
              <TableHead>Payment Terms</TableHead>
              <TableHead className="text-right">Total Invoiced</TableHead>
              <TableHead className="text-right">Outstanding Balance</TableHead>
              <TableHead className="text-center">Automated Outreach</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {customers.map((c) => {
              const isPaused = c.reminder_paused;

              return (
                <TableRow key={c.id}>
                  <TableCell className="font-semibold text-white">
                    <div>{c.name}</div>
                    {c.phone && (
                      <div className="text-[11px] text-slate-500 flex items-center gap-1 mt-0.5">
                        <Phone className="w-3 h-3" />
                        <span>{c.phone}</span>
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="text-xs text-slate-300">
                    <div className="flex items-center gap-1.5">
                      <Mail className="w-3 h-3 text-slate-500" />
                      <span>{c.email}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">
                      Net {c.payment_terms_days || 30}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right text-xs text-slate-300 numeric-mono">
                    {formatCurrency(c.total_invoiced || 0)}
                  </TableCell>
                  <TableCell className="text-right font-semibold text-white numeric-mono">
                    {formatCurrency(c.outstanding_balance || 0)}
                  </TableCell>
                  <TableCell className="text-center">
                    <button
                      onClick={() => onToggleReminder(c)}
                      title={isPaused ? 'Click to resume automated reminders' : 'Click to pause automated reminders'}
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all ${
                        isPaused
                          ? 'bg-amber-950/60 text-amber-300 border border-amber-800/40 hover:bg-amber-900/60'
                          : 'bg-emerald-950/60 text-emerald-300 border border-emerald-800/40 hover:bg-emerald-900/60'
                      }`}
                    >
                      {isPaused ? (
                        <>
                          <BellOff className="w-3 h-3 text-amber-400" />
                          <span>Paused</span>
                        </>
                      ) : (
                        <>
                          <Bell className="w-3 h-3 text-emerald-400" />
                          <span>Active</span>
                        </>
                      )}
                    </button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}
    </div>
  );
};
