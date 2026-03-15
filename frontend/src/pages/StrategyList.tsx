import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { STALE, REFRESH } from '@/lib/constants';
import { PageContainer } from '@/components/PageContainer';
import { PageHeader } from '@/components/PageHeader';
import { LoadingState, EmptyState, ErrorState } from '@/components';
import { StrategyCard } from '@/features/strategies/StrategyCard';
import type { Strategy } from '@/types/strategy';

export default function StrategyList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('all');
  const [marketFilter, setMarketFilter] = useState('all');
  const [search, setSearch] = useState('');

  const { data: strategies, isLoading, isError, refetch } = useQuery<Strategy[]>({
    queryKey: ['strategies'],
    queryFn: () => api.get('/strategies').then((r) => r.data),
    staleTime: STALE.strategyList,
    refetchInterval: REFRESH.strategyList,
  });

  const pauseMutation = useMutation({
    mutationFn: (id: string) => api.post(`/strategies/${id}/pause`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['strategies'] }),
  });

  const resumeMutation = useMutation({
    mutationFn: (id: string) => api.post(`/strategies/${id}/enable`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['strategies'] }),
  });

  const filtered = (strategies ?? []).filter((s) => {
    if (statusFilter !== 'all' && s.status !== statusFilter) return false;
    if (marketFilter !== 'all' && s.market !== marketFilter) return false;
    if (search && !s.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <PageContainer>
      <PageHeader title="Strategies" subtitle="Manage your trading strategies" />

      <div className="flex items-center justify-between mb-6">
        <div className="flex flex-wrap gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
          >
            <option value="all">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="enabled">Enabled</option>
            <option value="paused">Paused</option>
            <option value="disabled">Disabled</option>
          </select>
          <select
            value={marketFilter}
            onChange={(e) => setMarketFilter(e.target.value)}
            className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
          >
            <option value="all">All Markets</option>
            <option value="equities">Equities</option>
            <option value="forex">Forex</option>
          </select>
          <input
            type="text"
            placeholder="Search strategies..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary w-48"
          />
        </div>
        <button
          onClick={() => navigate('/strategies/new')}
          className="px-4 py-2 text-sm bg-accent text-white rounded hover:bg-accent/80 transition-colors"
        >
          + New Strategy
        </button>
      </div>

      {isLoading && <LoadingState rows={6} />}
      {isError && <ErrorState message="Failed to load strategies" onRetry={refetch} />}

      {!isLoading && !isError && (
        <>
          {filtered.length === 0 ? (
            <EmptyState
              message={
                strategies?.length === 0
                  ? 'No strategies yet. Create your first strategy.'
                  : 'No strategies match the current filters.'
              }
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {filtered.map((strategy) => (
                <StrategyCard
                  key={strategy.id}
                  strategy={strategy}
                  onPause={() => pauseMutation.mutate(strategy.id)}
                  onResume={() => resumeMutation.mutate(strategy.id)}
                  onEdit={() => navigate(`/strategies/${strategy.id}/edit`)}
                  onDetail={() => navigate(`/strategies/${strategy.id}`)}
                />
              ))}
            </div>
          )}
        </>
      )}
    </PageContainer>
  );
}
