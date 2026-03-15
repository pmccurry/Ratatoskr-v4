import { useAuth } from './useAuth';
import { PageContainer } from '@/components/PageContainer';
import { PageHeader } from '@/components/PageHeader';
import { Link } from 'react-router-dom';

export function AdminGuard({ children }: { children: React.ReactNode }) {
  const { isAdmin } = useAuth();

  if (!isAdmin) {
    return (
      <PageContainer>
        <PageHeader title="403 — Access Denied" />
        <div className="text-center py-12">
          <p className="text-text-secondary mb-4">
            You do not have permission to access this page.
          </p>
          <Link
            to="/dashboard"
            className="text-accent hover:text-accent-hover transition-colors"
          >
            Return to Dashboard
          </Link>
        </div>
      </PageContainer>
    );
  }

  return <>{children}</>;
}
