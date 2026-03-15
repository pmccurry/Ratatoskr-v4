import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { StatCard, CardGrid, LoadingState, ErrorState } from '@/components';

export function LatencyMetrics() {
  const { data: pipeline, isLoading, isError, refetch } = useQuery<Record<string, string>>({
    queryKey: ['observability', 'health', 'pipeline'],
    queryFn: () => api.get('/observability/health/pipeline').then((r) => r.data),
    staleTime: 5_000,
    refetchInterval: 10_000,
  });

  if (isLoading) return <LoadingState rows={2} />;
  if (isError) return <ErrorState message="Failed to load latency metrics" onRetry={refetch} />;
  if (!pipeline) return null;

  const metrics = [
    { label: 'Bar → DB', key: 'bar_to_db_ms' },
    { label: 'Evaluation', key: 'evaluation_ms' },
    { label: 'Signal → Risk', key: 'signal_to_risk_ms' },
    { label: 'Risk → Fill', key: 'risk_to_fill_ms' },
    { label: 'Fill → Position', key: 'fill_to_position_ms' },
  ];

  return (
    <CardGrid columns={5}>
      {metrics.map((m) => (
        <StatCard
          key={m.key}
          label={m.label}
          value={`${pipeline[m.key] ?? '—'} ms`}
        />
      ))}
    </CardGrid>
  );
}
