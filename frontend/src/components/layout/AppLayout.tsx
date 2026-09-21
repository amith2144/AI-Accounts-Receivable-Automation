import React, { useState } from 'react';
import { Sidebar, PageView } from './Sidebar';
import { Header } from './Header';

interface AppLayoutProps {
  currentPage: PageView;
  onSelectPage: (page: PageView) => void;
  onOpenUploadModal: () => void;
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  currentPage,
  onSelectPage,
  onOpenUploadModal,
  children,
}) => {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem('ar_sidebar_collapsed') === 'true';
    } catch {
      return false;
    }
  });

  const handleToggleSidebar = () => {
    setIsSidebarCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('ar_sidebar_collapsed', String(next));
      } catch {
        // ignore
      }
      return next;
    });
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#060709] text-slate-100 selection:bg-blue-600 selection:text-white">
      {/* Collapsible Sidebar */}
      <Sidebar
        currentPage={currentPage}
        onSelectPage={onSelectPage}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={handleToggleSidebar}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden min-w-0 relative bg-[#060709]">
        <Header
          currentPage={currentPage}
          onOpenUploadModal={onOpenUploadModal}
          isSidebarCollapsed={isSidebarCollapsed}
          onToggleSidebar={handleToggleSidebar}
        />

        <main className="flex-1 overflow-y-auto p-4 sm:p-6 bg-[#060709]">
          <div className="max-w-7xl mx-auto space-y-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};
