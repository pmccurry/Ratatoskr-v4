import { Outlet } from 'react-router-dom';
import { Sidebar } from '@/components/Sidebar';
import { AlertBanner } from '@/components/AlertBanner';
import { StatusBar } from '@/components/StatusBar';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { useUIStore } from '@/lib/store';
import { SIDEBAR_WIDTH } from '@/lib/constants';

export function AppShell() {
  const sidebarCollapsed = useUIStore((s) => s.sidebarCollapsed);
  const width = sidebarCollapsed ? SIDEBAR_WIDTH.collapsed : SIDEBAR_WIDTH.expanded;

  return (
    <div className="min-h-screen bg-background text-text-primary flex flex-col">
      <AlertBanner />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main
          className="flex-1 overflow-y-auto"
          style={{ marginLeft: width }}
        >
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
      <StatusBar sidebarWidth={width} />
    </div>
  );
}
