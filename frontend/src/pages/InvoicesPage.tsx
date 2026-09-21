import React, { useState } from 'react';
import { useInvoices } from '@/hooks/useInvoices';
import { InvoiceTable } from '@/components/invoices/InvoiceTable';
import { InvoiceUploadModal } from '@/components/invoices/InvoiceUploadModal';
import { InvoiceVerifyForm } from '@/components/invoices/InvoiceVerifyForm';
import { Dialog } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Invoice, DocumentImportStatus } from '@/types';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Upload, Ban } from 'lucide-react';

interface InvoicesPageProps {
  onRecordPayment: (invoice: Invoice) => void;
  isUploadModalOpen: boolean;
  setIsUploadModalOpen: (open: boolean) => void;
}

export const InvoicesPage: React.FC<InvoicesPageProps> = ({
  onRecordPayment,
  isUploadModalOpen,
  setIsUploadModalOpen,
}) => {
  const { invoices, isLoading, refetch, voidInvoice } = useInvoices();

  const [extractedData, setExtractedData] = useState<DocumentImportStatus | null>(null);
  const [isVerifyModalOpen, setIsVerifyModalOpen] = useState(false);
  const [selectedDetailInvoice, setSelectedDetailInvoice] = useState<Invoice | null>(null);
  const [voidingInvoice, setVoidingInvoice] = useState<Invoice | null>(null);
  const [voidReason, setVoidReason] = useState('');

  const handleExtractionSuccess = (data: DocumentImportStatus) => {
    setExtractedData(data);
    setIsVerifyModalOpen(true);
  };

  const handleConfirmSuccess = () => {
    refetch();
  };

  const handleConfirmVoid = async () => {
    if (!voidingInvoice) return;
    try {
      await voidInvoice.mutateAsync({ id: voidingInvoice.id, reason: voidReason || undefined });
      setVoidingInvoice(null);
      setVoidReason('');
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to void invoice.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white tracking-tight">Invoice Accounts Ledger</h2>
          <p className="text-xs text-slate-400">
            Real-time balance tracking, optical document parsing, and invoice lifecycle management
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsUploadModalOpen(true)}
            className="text-xs"
          >
            <Upload className="w-3.5 h-3.5 mr-1" />
            <span>Upload Document</span>
          </Button>
        </div>
      </div>

      {/* Main Table */}
      <InvoiceTable
        invoices={invoices}
        isLoading={isLoading}
        onRecordPayment={onRecordPayment}
        onVoidInvoice={(inv) => setVoidingInvoice(inv)}
        onSelectInvoiceDetail={(inv) => setSelectedDetailInvoice(inv)}
      />

      {/* Upload Modal */}
      <InvoiceUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onExtractionSuccess={handleExtractionSuccess}
      />

      {/* Side-by-Side Verification Form */}
      <InvoiceVerifyForm
        isOpen={isVerifyModalOpen}
        importData={extractedData}
        onClose={() => setIsVerifyModalOpen(false)}
        onConfirmSuccess={handleConfirmSuccess}
      />

      {/* Invoice Detail Modal */}
      <Dialog
        isOpen={!!selectedDetailInvoice}
        onClose={() => setSelectedDetailInvoice(null)}
        title={`Invoice ${selectedDetailInvoice?.invoice_number}`}
        description="Detailed record, status, and line items"
        maxWidth="lg"
      >
        {selectedDetailInvoice && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-lg bg-[#0e1017] border border-[#232634]">
                <span className="text-slate-400">Status</span>
                <div className="text-sm font-semibold text-white mt-1">
                  {selectedDetailInvoice.status}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-[#0e1017] border border-[#232634]">
                <span className="text-slate-400">Balance Due</span>
                <div className="text-sm font-semibold text-emerald-400 numeric-mono mt-1">
                  {formatCurrency(selectedDetailInvoice.balance_due, selectedDetailInvoice.currency)}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-[#0e1017] border border-[#232634]">
                <span className="text-slate-400">Issue Date</span>
                <div className="text-xs text-white mt-1">
                  {formatDate(selectedDetailInvoice.issue_date)}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-[#0e1017] border border-[#232634]">
                <span className="text-slate-400">Due Date</span>
                <div className="text-xs text-white mt-1">
                  {formatDate(selectedDetailInvoice.due_date)}
                </div>
              </div>
            </div>

            {selectedDetailInvoice.line_items && selectedDetailInvoice.line_items.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-[#1e212f]">
                <h4 className="text-xs font-semibold text-slate-300">Itemized Breakdown</h4>
                <div className="divide-y divide-[#1e212f] rounded-lg border border-[#232634] overflow-hidden">
                  {selectedDetailInvoice.line_items.map((li, i) => (
                    <div key={i} className="p-3 flex items-center justify-between text-xs bg-[#0e1017]">
                      <div>
                        <div className="text-white font-medium">{li.description}</div>
                        <div className="text-[11px] text-slate-500">
                          {Number(li.quantity)} × ${Number(li.unit_price).toFixed(2)}
                        </div>
                      </div>
                      <div className="font-semibold text-white numeric-mono">
                        ${Number(li.line_total).toFixed(2)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-3 border-t border-[#1e212f]">
              {Number(selectedDetailInvoice.balance_due) > 0 && selectedDetailInvoice.status !== 'VOID' && (
                <Button
                  variant="emerald"
                  size="sm"
                  onClick={() => {
                    const inv = selectedDetailInvoice;
                    setSelectedDetailInvoice(null);
                    onRecordPayment(inv);
                  }}
                >
                  Record Settlement
                </Button>
              )}
              <Button variant="ghost" size="sm" onClick={() => setSelectedDetailInvoice(null)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Dialog>

      {/* Void Confirmation Dialog */}
      <Dialog
        isOpen={!!voidingInvoice}
        onClose={() => setVoidingInvoice(null)}
        title="Void Invoice Confirmation"
        description="Voiding an invoice marks it uncollectible in the financial ledger."
        maxWidth="md"
      >
        {voidingInvoice && (
          <div className="space-y-4">
            <p className="text-xs text-slate-300">
              Are you sure you want to void invoice <strong className="text-white">{voidingInvoice.invoice_number}</strong> with balance{' '}
              <strong className="text-white">{formatCurrency(voidingInvoice.balance_due)}</strong>?
            </p>

            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-400">Reason / Justification (Audited)</label>
              <input
                type="text"
                value={voidReason}
                onChange={(e) => setVoidReason(e.target.value)}
                placeholder="e.g. Customer dispute settlement, duplicate billing"
                className="w-full h-9 px-3 rounded-md bg-[#0c0d14] border border-[#232634] text-xs text-white"
              />
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-[#1e212f]">
              <Button variant="ghost" size="sm" onClick={() => setVoidingInvoice(null)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleConfirmVoid}
                isLoading={voidInvoice.isPending}
              >
                <Ban className="w-3.5 h-3.5 mr-1" />
                <span>Confirm Void</span>
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
};
