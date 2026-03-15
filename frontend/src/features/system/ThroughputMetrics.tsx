import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { StatCard, CardGrid, LoadingState, ErrorState } from '@/components';

// TODO: Add per-metric sparkline charts using time-series data from /observability/health/pipeline/history
// Deferred — requires a new backend endpoint that returns historical throughput snapshots.
export function ThroughputMetrics() {
  const { data: pipeline, isLoading, isError, refetch } = useQuery<Record<string, string>>({
    queryKey: ['observability', 'health', 'pipeline'],
    queryFn: () => api.get('/observability/health/pipeline').then((r) => r.data),
    staleTime: 5_000,
    refetchInterval: 10_000,
  });

  if (isLoading) return <LoadingState rows={2} />;
  if (isError) return <ErrorState message="Failed to load throughput metrics" onRetry={refetch} />;
  if (!pipeline) return null;

  const metrics = [
    { label: 'Bars/min', key: 'bars_per_min' },
    { label: 'Evaluations/min', key: 'evaluations_per_min' },
    { label: 'Signals/min', key: 'signals_per_min' },
    { label: 'Fills/min', key: 'fills_per_min' },
  ];

  return (
    <CardGrid columns={4}>
      {metrics.map((m) => (
        <StatCard
          key={m.key}
          label={m.label}
          value={pipeline[m.key] ?? '0'}
        />
      ))}
    </CardGrid>
  );
}
