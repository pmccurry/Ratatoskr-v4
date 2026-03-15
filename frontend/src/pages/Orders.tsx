import { PageContainer } from '@/components/PageContainer';
import { PageHeader } from '@/components/PageHeader';
import { TabContainer } from '@/components/TabContainer';
import { OrderTable } from '@/features/orders/OrderTable';
import { FillTable } from '@/features/orders/FillTable';
import { ForexPoolStatus } from '@/features/orders/ForexPoolStatus';
import { ShadowComparison } from '@/features/orders/ShadowComparison';

const TABS = [
  { key: 'orders', label: 'Orders' },
  { key: 'fills', label: 'Fills' },
  { key: 'forex-pool', label: 'Forex Pool' },
  { key: 'shadow', label: 'Shadow Tracking' },
];

export default function Orders() {
  return (
    <PageContainer>
      <PageHeader title="Orders & Fills" subtitle="Paper trading execution" />
      <TabContainer tabs={TABS}>
        {(activeTab) => (
          <>
            {activeTab === 'orders' && <OrderTable />}
            {activeTab === 'fills' && <FillTable />}
            {activeTab === 'forex-pool' && <ForexPoolStatus />}
            {activeTab === 'shadow' && <ShadowComparison />}
          </>
        )}
      </TabContainer>
    </PageContainer>
  );
}
