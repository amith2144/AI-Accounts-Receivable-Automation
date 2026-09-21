import React, { useState } from 'react';
import { useCustomers } from '@/hooks/useCustomers';
import { CustomerList } from '@/components/customers/CustomerList';
import { CustomerModal } from '@/components/customers/CustomerModal';
import { Button } from '@/components/ui/button';
import { Customer } from '@/types';
import { Plus, Search } from 'lucide-react';

export const CustomersPage: React.FC = () => {
  const { customers, isLoading, search, setSearch, refetch, toggleReminder } = useCustomers();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const handleToggleReminder = async (customer: Customer) => {
    try {
      await toggleReminder.mutateAsync({
        id: customer.id,
        paused: !customer.reminder_paused,
      });
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to update reminder status.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white tracking-tight">Debtor Directory & Accounts</h2>
          <p className="text-xs text-slate-400">
            Manage customer credit agreements, terms, balances, and autonomous outreach overrides
          </p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by customer name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full h-8 pl-8 pr-3 rounded-md bg-[#0e1017] border border-[#232634] text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsCreateModalOpen(true)}
            className="text-xs shrink-0"
          >
            <Plus className="w-3.5 h-3.5 mr-1" />
            <span>New Customer</span>
          </Button>
        </div>
      </div>

      {/* Customer Directory Table */}
      <CustomerList
        customers={customers}
        isLoading={isLoading}
        onToggleReminder={handleToggleReminder}
      />

      {/* Create Customer Profile Modal */}
      <CustomerModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={() => refetch()}
      />
    </div>
  );
};
