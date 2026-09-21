import React, { useState } from 'react';
import { Dialog } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DocumentImportStatus } from '@/types';
import { invoiceService } from '@/services/invoiceService';
import { CheckCircle2, AlertCircle, Check, Plus, Trash2 } from 'lucide-react';

interface InvoiceVerifyFormProps {
  importData: DocumentImportStatus | null;
  isOpen: boolean;
  onClose: () => void;
  onConfirmSuccess: () => void;
}

export const InvoiceVerifyForm: React.FC<InvoiceVerifyFormProps> = ({
  importData,
  isOpen,
  onClose,
  onConfirmSuccess,
}) => {
  if (!importData) return null;

  const raw = importData.extracted_data || {};

  const [invoiceNumber, setInvoiceNumber] = useState(raw.invoice_number || 'INV-2026-001');
  const [customerName, setCustomerName] = useState(raw.customer_name || 'Acme Logistics Corp');
  const [customerEmail, setCustomerEmail] = useState(raw.customer_email || 'billing@acmelogistics.com');
  const [issueDate, setIssueDate] = useState(raw.issue_date || new Date().toISOString().slice(0, 10));
  const [dueDate, setDueDate] = useState(raw.due_date || new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10));
  const [totalAmount, setTotalAmount] = useState(raw.total_amount ? String(raw.total_amount) : '1500.00');

  const [lineItems, setLineItems] = useState(
    raw.line_items && raw.line_items.length > 0
      ? raw.line_items.map((li) => ({
          description: li.description,
          quantity: Number(li.quantity) || 1,
          unit_price: Number(li.unit_price) || 0,
          line_total: Number(li.line_total || (Number(li.quantity) * Number(li.unit_price))),
        }))
      : [
          {
            description: 'Logistics and freight distribution services',
            quantity: 1,
            unit_price: 1500.0,
            line_total: 1500.0,
          },
        ]
  );

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAddLine = () => {
    setLineItems([
      ...lineItems,
      { description: 'Consulting services', quantity: 1, unit_price: 100.0, line_total: 100.0 },
    ]);
  };

  const handleRemoveLine = (index: number) => {
    setLineItems(lineItems.filter((_, i) => i !== index));
  };

  const handleLineChange = (index: number, field: string, val: any) => {
    const updated = [...lineItems];
    (updated[index] as any)[field] = val;
    if (field === 'quantity' || field === 'unit_price') {
      const q = field === 'quantity' ? Number(val) : updated[index].quantity;
      const p = field === 'unit_price' ? Number(val) : updated[index].unit_price;
      updated[index].line_total = q * p;
    }
    setLineItems(updated);

    // Auto update total
    const sum = updated.reduce((acc, li) => acc + (Number(li.line_total) || 0), 0);
    setTotalAmount(sum.toFixed(2));
  };

  const handleConfirm = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      await invoiceService.confirmImport(importData.document_id, {
        invoice_number: invoiceNumber,
        customer_name: customerName,
        customer_email: customerEmail,
        issue_date: issueDate,
        due_date: dueDate,
        currency: 'USD',
        total_amount: parseFloat(totalAmount),
        line_items: lineItems.map((li) => ({
          description: li.description,
          quantity: li.quantity,
          unit_price: li.unit_price,
          line_total: li.line_total,
        })),
      });

      onConfirmSuccess();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to confirm invoice import.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Verify & Confirm Extracted Invoice"
      description={`Source Document: ${importData.original_filename} (Review extracted fields before committing to ledger)`}
      maxWidth="2xl"
    >
      <div className="space-y-5">
        {error && (
          <div className="p-3 rounded-md bg-red-950/50 border border-red-800/60 text-red-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Verification Alert */}
        <div className="p-3 rounded-lg bg-blue-950/30 border border-blue-800/40 text-blue-300 text-xs flex items-center gap-2.5">
          <CheckCircle2 className="w-4 h-4 text-blue-400 shrink-0" />
          <span>
            OCR extraction completed. You can adjust any parsed values below prior to issuing the invoice.
          </span>
        </div>

        {/* Form Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Invoice Number"
            value={invoiceNumber}
            onChange={(e) => setInvoiceNumber(e.target.value)}
            required
          />
          <Input
            label="Total Amount ($ USD)"
            type="number"
            step="0.01"
            value={totalAmount}
            onChange={(e) => setTotalAmount(e.target.value)}
            required
          />
          <Input
            label="Debtor Business / Customer"
            value={customerName}
            onChange={(e) => setCustomerName(e.target.value)}
            required
          />
          <Input
            label="Customer Billing Email"
            type="email"
            value={customerEmail}
            onChange={(e) => setCustomerEmail(e.target.value)}
            required
          />
          <Input
            label="Invoice Issue Date"
            type="date"
            value={issueDate}
            onChange={(e) => setIssueDate(e.target.value)}
            required
          />
          <Input
            label="Payment Due Date"
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            required
          />
        </div>

        {/* Line Items Table */}
        <div className="space-y-2 pt-2 border-t border-[#1e212f]">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-slate-200">Itemized Billing Lines</label>
            <Button variant="ghost" size="sm" onClick={handleAddLine} className="text-xs text-blue-400">
              <Plus className="w-3.5 h-3.5 mr-1" />
              <span>Add Line</span>
            </Button>
          </div>

          <div className="space-y-2">
            {lineItems.map((li, idx) => (
              <div key={idx} className="flex items-center gap-2 p-2.5 rounded-lg bg-[#0e1017] border border-[#232634]">
                <div className="flex-1">
                  <input
                    type="text"
                    placeholder="Description"
                    value={li.description}
                    onChange={(e) => handleLineChange(idx, 'description', e.target.value)}
                    className="w-full h-8 px-2 rounded bg-[#161823] border border-[#232638] text-xs text-white"
                  />
                </div>
                <div className="w-20">
                  <input
                    type="number"
                    placeholder="Qty"
                    value={li.quantity}
                    onChange={(e) => handleLineChange(idx, 'quantity', e.target.value)}
                    className="w-full h-8 px-2 rounded bg-[#161823] border border-[#232638] text-xs text-white text-right"
                  />
                </div>
                <div className="w-28">
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Unit Price"
                    value={li.unit_price}
                    onChange={(e) => handleLineChange(idx, 'unit_price', e.target.value)}
                    className="w-full h-8 px-2 rounded bg-[#161823] border border-[#232638] text-xs text-white text-right"
                  />
                </div>
                <div className="w-28 text-right text-xs font-semibold text-white numeric-mono pr-2">
                  ${Number(li.line_total || 0).toFixed(2)}
                </div>
                <button
                  type="button"
                  onClick={() => handleRemoveLine(idx)}
                  className="p-1 rounded text-slate-500 hover:text-red-400 hover:bg-red-950/30"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#1e212f]">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            variant="emerald"
            size="sm"
            onClick={handleConfirm}
            isLoading={isSubmitting}
          >
            <Check className="w-4 h-4 mr-1.5" />
            <span>Confirm Import & Issue Invoice</span>
          </Button>
        </div>
      </div>
    </Dialog>
  );
};
