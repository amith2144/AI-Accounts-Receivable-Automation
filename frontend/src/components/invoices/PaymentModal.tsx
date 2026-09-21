import React, { useState, useEffect } from 'react';
import { Dialog } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/select';
import { Invoice, PaymentMethod } from '@/types';
import { paymentService } from '@/services/paymentService';
import { formatCurrency } from '@/lib/utils';
import { CreditCard, AlertCircle } from 'lucide-react';

interface PaymentModalProps {
  invoice: Invoice | null;
  isOpen: boolean;
  onClose: () => void;
  onPaymentSuccess: () => void;
}

export const PaymentModal: React.FC<PaymentModalProps> = ({
  invoice,
  isOpen,
  onClose,
  onPaymentSuccess,
}) => {
  if (!invoice) return null;

  const [amount, setAmount] = useState<string>('');
  const [paymentDate, setPaymentDate] = useState<string>(new Date().toISOString().slice(0, 10));
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('ACH');
  const [referenceNumber, setReferenceNumber] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (invoice) {
      // Default amount to full outstanding balance
      setAmount(String(invoice.balance_due));
      setError(null);
    }
  }, [invoice]);

  const maxBalance = Number(invoice.balance_due);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const numAmount = parseFloat(amount);
    if (isNaN(numAmount) || numAmount <= 0) {
      setError('Please enter a valid positive payment amount.');
      return;
    }

    if (numAmount > maxBalance) {
      setError(`Payment cannot exceed outstanding balance of ${formatCurrency(maxBalance, invoice.currency)}.`);
      return;
    }

    setIsSubmitting(true);
    try {
      await paymentService.recordPayment(invoice.id, {
        amount: numAmount,
        payment_date: paymentDate,
        payment_method: paymentMethod,
        reference_number: referenceNumber || undefined,
        notes: notes || undefined,
      });

      onPaymentSuccess();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to record settlement.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const isFullPayment = Number(amount) === maxBalance;

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Record Payment Settlement"
      description={`Apply full or partial payment against Invoice #${invoice.invoice_number}`}
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 rounded-md bg-red-950/50 border border-red-800/60 text-red-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Balance Overview Card */}
        <div className="p-3 rounded-lg bg-[#0e1017] border border-[#232634] flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400">Current Balance Due</div>
            <div className="text-xl font-bold text-white numeric-mono mt-0.5">
              {formatCurrency(invoice.balance_due, invoice.currency)}
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-slate-400">Total Invoice Amount</div>
            <div className="text-xs text-slate-300 numeric-mono mt-0.5">
              {formatCurrency(invoice.total_amount, invoice.currency)}
            </div>
          </div>
        </div>

        {/* Payment Amount */}
        <div className="space-y-1">
          <Input
            label="Settlement Amount ($ USD)"
            type="number"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            required
            helperText={
              isFullPayment
                ? 'Full settlement — invoice status will transition to PAID.'
                : 'Partial settlement — remaining balance will stay active.'
            }
          />
        </div>

        {/* Payment Date & Method */}
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Payment Date"
            type="date"
            value={paymentDate}
            onChange={(e) => setPaymentDate(e.target.value)}
            required
          />

          <Select
            label="Remittance Channel"
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod)}
            options={[
              { value: 'ACH', label: 'ACH Direct Debit' },
              { value: 'WIRE', label: 'Bank Wire Transfer' },
              { value: 'CHECK', label: 'Paper / Lockbox Check' },
              { value: 'CREDIT_CARD', label: 'Credit Card' },
              { value: 'OTHER', label: 'Other / Journal Entry' },
            ]}
          />
        </div>

        {/* Reference & Notes */}
        <Input
          label="Transaction / Check Ref # (Optional)"
          value={referenceNumber}
          onChange={(e) => setReferenceNumber(e.target.value)}
          placeholder="e.g. TR-98231 or CHK-4029"
        />

        <Textarea
          label="Remittance Notes (Optional)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Internal notes or customer remittance memo..."
        />

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#1e212f]">
          <Button variant="ghost" size="sm" type="button" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button variant="emerald" size="sm" type="submit" isLoading={isSubmitting}>
            <CreditCard className="w-3.5 h-3.5 mr-1" />
            <span>Apply Settlement</span>
          </Button>
        </div>
      </form>
    </Dialog>
  );
};
