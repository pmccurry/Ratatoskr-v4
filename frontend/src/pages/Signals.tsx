import { PageContainer } from '@/components/PageContainer';
import { PageHeader } from '@/components/PageHeader';
import { SignalStats } from '@/features/signals/SignalStats';
import { SignalTable } from '@/features/signals/SignalTable';

export default function Signals() {
  return (
    <PageContainer>
      <PageHeader title="Signals" subtitle="Signal generation and lifecycle" />
      <div className="space-y-6">
        <SignalStats />
        <SignalTable />
      </div>
    </PageContainer>
  );
}
