import { PageContainer } from '@/components/PageContainer';
import { PageHeader } from '@/components/PageHeader';
import { KillSwitchControl } from '@/features/risk/KillSwitchControl';
import { RiskStatCards } from '@/features/risk/RiskStatCards';
import { ExposureBreakdown } from '@/features/risk/ExposureBreakdown';
import { RiskDecisionTable } from '@/features/risk/RiskDecisionTable';
import { RiskConfigSummary } from '@/features/risk/RiskConfigSummary';

export default function Risk() {
  return (
    <PageContainer>
      <PageHeader title="Risk Dashboard" subtitle="Exposure, drawdown, and controls" />

      <div className="space-y-6">
        <KillSwitchControl />
        <RiskStatCards />
        <ExposureBreakdown />
        <RiskDecisionTable />
        <RiskConfigSummary />
      </div>
    </PageContainer>
  );
}
