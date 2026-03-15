import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { STALE, REFRESH, COLORS } from '@/lib/constants';
import { LoadingState, ErrorState } from '@/components';
import type { SystemHealth } from '@/types/observability';

export function PipelineStatus() {
  const { data: health, isLoading, isError, refetch } = useQuery<SystemHealth>({
    queryKey: ['observability', 'health'],
    queryFn: () => api.get('/observability/health').then((r) => r.data),
    staleTime: STALE.systemHealth,
    refetchInterval: REFRESH.systemHealth,
  });

  const { data: activeAlerts } = useQuery<unknown[]>({
    queryKey: ['observability', 'alerts', 'active'],
    queryFn: () => api.get('/observability/alerts/active').then((r) => r.data),
    staleTime: STALE.systemHealth,
    refetchInterval: REFRESH.systemHealth,
  });

  if (isLoading) return <LoadingState rows={4} />;
  if (isError) return <ErrorState message="Failed to load system health" onRetry={refetch} />;
  if (!health) return null;

  const statusColor =
    health.overallStatus === 'healthy'
      ? COLORS.success
      : health.overallStatus === 'degraded'
        ? COLORS.warning
        : COLORS.error;

  const formatUptime = (seconds: number): string => {
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${d}d ${h}h ${m}m`;
  };

  const moduleEntries = Object.entries(health.modules);
  const alertCount = activeAlerts?.length ?? 0;

  return (
    <div className="bg-surface rounded-lg border border-border p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span
            className="inline-block h-4 w-4 rounded-full"
            style={{ backgroundColor: statusColor }}
          />
          <span className="text-lg font-semibold text-text-primary capitalize">
            {health.overallStatus}
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-text-secondary">
            Uptime: <span className="font-mono text-text-primary">{formatUptime(health.uptimeSeconds)}</span>
          </span>
          {alertCount > 0 && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-error/20 text-error">
              {alertCount} active alert{alertCount !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-medium text-text-secondary">Modules</h3>
        <div className="grid grid-cols-2 gap-2">
          {moduleEntries.map(([name, mod]) => {
            const dotColor =
              ['healthy', 'ok', 'running'].includes(mod.status)
                ? COLORS.success
                : ['degraded', 'unknown', 'warning'].includes(mod.status)
                  ? COLORS.warning
                  : COLORS.error;
            return (
              <div key={name} className="flex items-center gap-2 py-1">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: dotColor }}
                />
                <span className="text-sm text-text-primary">{name}</span>
                <span className="text-xs text-text-tertiary capitalize">{mod.status}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
