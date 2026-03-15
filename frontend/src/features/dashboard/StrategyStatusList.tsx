import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import { REFRESH, STALE } from '@/lib/constants';

import { SectionHeader, StatusPill, TimeAgo, LoadingState, EmptyState, ErrorState } from '@/components';
import type { Strategy } from '@/types/strategy';

const STATUS_DOT: Record<string, string> = {
  enabled: 'bg-success',
  paused: 'bg-warning',
  disabled: 'bg-text-tertiary',
  draft: 'bg-text-tertiary',
  error: 'bg-error',
};

export function StrategyStatusList() {
  const navigate = useNavigate();

  const { data: strategies, isLoading, isError, refetch } = useQuery<Strategy[]>({
    queryKey: ['strategies'],
    queryFn: () => api.get('/strategies').then((r) => r.data),
    staleTime: STALE.strategyList,
    refetchInterval: REFRESH.strategyList,
  });

  return (
    <div className="bg-surface rounded-lg border border-border p-4">
      <SectionHeader title="Strategies" />
      {isLoading ? (
        <LoadingState rows={5} />
      ) : isError ? (
        <ErrorState message="Failed to load strategies" onRetry={refetch} />
      ) : !strategies?.length ? (
        <EmptyState message="No strategies created yet" />
      ) : (
        <div className="space-y-1 mt-3">
          {strategies.map((s) => (
            <button
              key={s.id}
              onClick={() => navigate(`/strategies/${s.id}`)}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-surface-hover transition-colors text-left"
            >
              <span className={`w-2 h-2 rounded-full shrink-0 ${STATUS_DOT[s.status] ?? 'bg-text-tertiary'}`} />
              <span className="flex-1 text-sm text-text-primary truncate">{s.name}</span>
              <StatusPill status={s.status} />
              <span className="text-xs text-text-tertiary">
                {s.lastEvaluatedAt ? <TimeAgo value={s.lastEvaluatedAt} /> : 'never'}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
