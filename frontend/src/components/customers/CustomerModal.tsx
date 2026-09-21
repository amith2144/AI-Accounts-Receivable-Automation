import React, { useState } from 'react';
import { Dialog } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { useCustomers } from '@/hooks/useCustomers';
import { AlertCircle } from 'lucide-react';

interface CustomerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const CustomerModal: React.FC<CustomerModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { createCustomer } = useCustomers();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [terms, setTerms] = useState('30');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await createCustomer.mutateAsync({
        name,
        email,
        phone: phone || undefined,
        payment_terms_days: parseInt(terms, 10),
      });
      setName('');
      setEmail('');
      setPhone('');
      setTerms('30');
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create customer profile.');
    }
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Create Debtor Customer Profile"
      description="Register a new customer account, billing contact, and payment terms"
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 rounded-md bg-red-950/50 border border-red-800/60 text-red-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <Input
          label="Business / Customer Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Acme Corporation"
          required
        />

        <Input
          label="Billing Remittance Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="billing@acme.com"
          required
        />

        <Input
          label="Telephone (Optional)"
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="+1 (555) 019-2834"
        />

        <Select
          label="Standard Payment Terms"
          value={terms}
          onChange={(e) => setTerms(e.target.value)}
          options={[
            { value: '15', label: 'Net 15 Days' },
            { value: '30', label: 'Net 30 Days (Standard)' },
            { value: '45', label: 'Net 45 Days' },
            { value: '60', label: 'Net 60 Days' },
            { value: '90', label: 'Net 90 Days' },
          ]}
        />

        <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#1e212f]">
          <Button variant="ghost" size="sm" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" size="sm" type="submit" isLoading={createCustomer.isPending}>
            Create Customer Profile
          </Button>
        </div>
      </form>
    </Dialog>
  );
};
