import { PageContainer } from '@/components/PageContainer';
import { PageHeader } from '@/components/PageHeader';
import { TabContainer } from '@/components/TabContainer';
import { PipelineStatus } from '@/features/system/PipelineStatus';
import { ThroughputMetrics } from '@/features/system/ThroughputMetrics';
import { LatencyMetrics } from '@/features/system/LatencyMetrics';
import { BackgroundJobs } from '@/features/system/BackgroundJobs';
import { DatabaseStats } from '@/features/system/DatabaseStats';
import { ActivityFeed } from '@/features/dashboard/ActivityFeed';

const TABS = [
  { key: 'health', label: 'Health' },
  { key: 'pipeline', label: 'Pipeline' },
  { key: 'activity', label: 'Activity' },
  { key: 'jobs', label: 'Jobs' },
  { key: 'database', label: 'Database' },
];

export default function System() {
  return (
    <PageContainer>
      <PageHeader title="System Telemetry" subtitle="Pipeline status and activity feed" />
      <TabContainer tabs={TABS}>
        {(activeTab) => (
          <>
            {activeTab === 'health' && <PipelineStatus />}
            {activeTab === 'pipeline' && (
              <div className="space-y-6">
                <ThroughputMetrics />
                <LatencyMetrics />
              </div>
            )}
            {activeTab === 'activity' && <ActivityFeed />}
            {activeTab === 'jobs' && <BackgroundJobs />}
            {activeTab === 'database' && <DatabaseStats />}
          </>
        )}
      </TabContainer>
    </PageContainer>
  );
}
