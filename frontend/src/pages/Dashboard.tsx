import { PageContainer } from '@/components/PageContainer';
import { PageHeader } from '@/components/PageHeader';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { StatCards } from '@/features/dashboard/StatCards';
import { EquityCurveChart } from '@/features/dashboard/EquityCurveChart';
import { StrategyStatusList } from '@/features/dashboard/StrategyStatusList';
import { ActivityFeed } from '@/features/dashboard/ActivityFeed';

function WidgetError({ label }: { label: string }) {
  return (
    <div className="bg-surface rounded-lg border border-border p-4 text-text-secondary text-sm">
      Failed to load {label}
    </div>
  );
}

export default function Dashboard() {
  return (
    <PageContainer>
      <PageHeader title="Dashboard" subtitle="Portfolio overview and activity" />
      <div className="space-y-6">
        <ErrorBoundary fallback={<WidgetError label="stats" />}>
          <StatCards />
        </ErrorBoundary>
        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-2">
            <ErrorBoundary fallback={<WidgetError label="equity curve" />}>
              <EquityCurveChart />
            </ErrorBoundary>
          </div>
          <div className="col-span-1">
            <ErrorBoundary fallback={<WidgetError label="strategy status" />}>
              <StrategyStatusList />
            </ErrorBoundary>
          </div>
        </div>
        <ErrorBoundary fallback={<WidgetError label="activity feed" />}>
          <ActivityFeed />
        </ErrorBoundary>
      </div>
    </PageContainer>
  );
}
