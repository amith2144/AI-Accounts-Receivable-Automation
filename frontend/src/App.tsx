import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import { AppLayout } from '@/components/layout/AppLayout';
import { PageView } from '@/components/layout/Sidebar';
import { LoginPage } from '@/pages/LoginPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { InvoicesPage } from '@/pages/InvoicesPage';
import { CustomersPage } from '@/pages/CustomersPage';
import { CadencesPage } from '@/pages/CadencesPage';
import { PaymentModal } from '@/components/invoices/PaymentModal';
import { Invoice } from '@/types';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const AuthenticatedApp: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const [currentPage, setCurrentPage] = useState<PageView>('dashboard');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedPaymentInvoice, setSelectedPaymentInvoice] = useState<Invoice | null>(null);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#090a0f] flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto" />
          <p className="text-xs text-slate-400 font-medium tracking-wide">
            Initializing Secure Financial Session...
          </p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return (
          <DashboardPage
            onSelectInvoiceForPayment={(inv) => setSelectedPaymentInvoice(inv)}
            onNavigateToInvoices={() => setCurrentPage('invoices')}
          />
        );
      case 'invoices':
        return (
          <InvoicesPage
            onRecordPayment={(inv) => setSelectedPaymentInvoice(inv)}
            isUploadModalOpen={isUploadModalOpen}
            setIsUploadModalOpen={setIsUploadModalOpen}
          />
        );
      case 'customers':
        return <CustomersPage />;
      case 'cadences':
        return <CadencesPage />;
      default:
        return (
          <DashboardPage
            onSelectInvoiceForPayment={(inv) => setSelectedPaymentInvoice(inv)}
            onNavigateToInvoices={() => setCurrentPage('invoices')}
          />
        );
    }
  };

  return (
    <AppLayout
      currentPage={currentPage}
      onSelectPage={(page) => setCurrentPage(page)}
      onOpenUploadModal={() => setIsUploadModalOpen(true)}
    >
      {renderCurrentPage()}

      {/* Global Payment Settlement Modal */}
      <PaymentModal
        invoice={selectedPaymentInvoice}
        isOpen={!!selectedPaymentInvoice}
        onClose={() => setSelectedPaymentInvoice(null)}
        onPaymentSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['invoices'] });
          queryClient.invalidateQueries({ queryKey: ['dashboard'] });
          queryClient.invalidateQueries({ queryKey: ['customers'] });
          queryClient.invalidateQueries({ queryKey: ['activities'] });
        }}
      />
    </AppLayout>
  );
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AuthenticatedApp />
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;
