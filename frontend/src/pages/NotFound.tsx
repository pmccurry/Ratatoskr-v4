import { Link } from 'react-router-dom';
import { PageContainer } from '@/components/PageContainer';
import { PageHeader } from '@/components/PageHeader';

export default function NotFound() {
  return (
    <PageContainer>
      <PageHeader title="404 — Page Not Found" />
      <div className="text-center py-12">
        <p className="text-text-secondary mb-4">
          The page you are looking for does not exist.
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
