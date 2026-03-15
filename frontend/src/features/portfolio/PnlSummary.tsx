import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { CardGrid, StatCard, SectionHeader, LoadingState, ErrorState } from '@/components';
import { PnlValue } from '@/components';
import { formatCurrency } from '@/lib/formatters';

interface PnlSummaryResponse {
  today: number;
  thisWeek: number;
  thisMonth: number;
  total: number;
  byStrategy: Record<string, number>;
  bySymbol: Record<string, number>;
}

function pnlTrend(value: number): 'up' | 'down' | undefined {
  if (value > 0) return 'up';
  if (value < 0) return 'down';
  return undefined;
}

export function PnlSummary() {
  const { data, isLoading, isError, refetch } = useQuery<PnlSummaryResponse>({
    queryKey: ['portfolio', 'pnl', 'summary'],
    queryFn: () => api.get('/portfolio/pnl/summary').then((r) => r.data),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  if (isLoading) return <LoadingState rows={4} />;
  if (isError) return <ErrorState message="Failed to load PnL summary" onRetry={refetch} />;
  if (!data) return null;

  const strategyEntries = Object.entries(data.byStrategy);
  const symbolEntries = Object.entries(data.bySymbol);

  return (
    <div>
      <CardGrid columns={4}>
        <StatCard
          label="Today's PnL"
          value={formatCurrency(data.today)}
          trend={pnlTrend(data.today)}
        />
        <StatCard
          label="This Week"
          value={formatCurrency(data.thisWeek)}
          trend={pnlTrend(data.thisWeek)}
        />
        <StatCard
          label="This Month"
          value={formatCurrency(data.thisMonth)}
          trend={pnlTrend(data.thisMonth)}
        />
        <StatCard
          label="Total PnL"
          value={formatCurrency(data.total)}
          trend={pnlTrend(data.total)}
        />
      </CardGrid>

      <div className="grid grid-cols-2 gap-6 mt-6">
        <div>
          <SectionHeader title="By Strategy" />
          <div className="flex flex-col gap-1 mt-2">
            {strategyEntries.length === 0 ? (
              <p className="text-sm text-text-tertiary">No strategy data</p>
            ) : (
              strategyEntries.map(([id, pnl]) => (
                <div key={id} className="flex justify-between items-center py-1">
                  <span className="text-sm text-text-secondary truncate max-w-[180px]" title={id}>
                    {id.slice(0, 8)}...
                  </span>
                  <PnlValue value={pnl} />
                </div>
              ))
            )}
          </div>
        </div>
        <div>
          <SectionHeader title="By Symbol" />
          <div className="flex flex-col gap-1 mt-2">
            {symbolEntries.length === 0 ? (
              <p className="text-sm text-text-tertiary">No symbol data</p>
            ) : (
              symbolEntries.map(([symbol, pnl]) => (
                <div key={symbol} className="flex justify-between items-center py-1">
                  <span className="text-sm text-text-secondary">{symbol}</span>
                  <PnlValue value={pnl} />
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
