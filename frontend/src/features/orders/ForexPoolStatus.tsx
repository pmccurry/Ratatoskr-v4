import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { SectionHeader, LoadingState, EmptyState, ErrorState, TimeAgo } from '@/components';

interface ForexAccount {
  accountId: string;
  label: string;
  allocations: Array<{
    symbol: string;
    side: string;
    strategyId: string;
    strategyName: string;
    since: string;
  }>;
}

interface ForexPoolResponse {
  accounts: ForexAccount[];
  pairCapacity: Record<string, { occupied: number; total: number }>;
}

export function ForexPoolStatus() {
  const { data: pool, isLoading, isError, refetch } = useQuery<ForexPoolResponse>({
    queryKey: ['paper-trading', 'forex-pool', 'status'],
    queryFn: () => api.get('/paper-trading/forex-pool/status').then((r) => r.data),
    staleTime: 30_000,
    refetchInterval: 30_000,
  });

  if (isLoading) return <LoadingState rows={4} />;
  if (isError) return <ErrorState message="Failed to load forex pool status" onRetry={refetch} />;
  if (!pool || !pool.accounts.length) return <EmptyState message="No forex accounts configured" />;

  const pairEntries = Object.entries(pool.pairCapacity);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        {pool.accounts.map((account) => (
          <div
            key={account.accountId}
            className="bg-surface rounded-lg border border-border p-4"
          >
            <div className="text-sm font-medium text-text-primary mb-2">
              {account.label}
            </div>
            {account.allocations.length === 0 ? (
              <span className="text-success text-sm">Available</span>
            ) : (
              <div className="space-y-2">
                {account.allocations.map((alloc) => (
                  <div
                    key={`${alloc.symbol}-${alloc.strategyId}`}
                    className="text-sm text-text-secondary"
                  >
                    <span className="font-mono text-text-primary">{alloc.symbol}</span>
                    {' '}
                    <span className={alloc.side === 'buy' ? 'text-success' : 'text-error'}>
                      {alloc.side.toUpperCase()}
                    </span>
                    {' — '}
                    <span>{alloc.strategyName}</span>
                    {' — '}
                    <TimeAgo value={alloc.since} />
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {pairEntries.length > 0 && (
        <div>
          <SectionHeader title="Pair Capacity" />
          <div className="space-y-3">
            {pairEntries.map(([pair, cap]) => {
              const pct = cap.total > 0 ? (cap.occupied / cap.total) * 100 : 0;
              return (
                <div key={pair} className="flex items-center gap-3">
                  <span className="text-sm font-mono text-text-primary w-20">{pair}</span>
                  <div className="flex-1 bg-border rounded-full h-2">
                    <div
                      className="bg-accent rounded-full h-2 transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-sm text-text-secondary w-12 text-right">
                    {cap.occupied} / {cap.total}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
