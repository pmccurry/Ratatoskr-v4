import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { formatPercent } from '@/lib/formatters';
import type { SignalStats as SignalStatsType } from '@/types/signal';

export function SignalStats() {
  const { data, isLoading, isError } = useQuery<SignalStatsType>({
    queryKey: ['signals', 'stats'],
    queryFn: () => api.get('/signals/stats').then((r) => r.data),
    staleTime: 30_000,
    refetchInterval: 30_000,
  });

  if (isError) {
    return (
      <div className="bg-surface rounded-lg border border-border p-4 text-error text-sm">
        Failed to load signal stats
      </div>
    );
  }

  if (isLoading || !data) {
    return (
      <div className="bg-surface rounded-lg border border-border p-4">
        <div className="flex gap-6 animate-pulse">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="flex flex-col gap-1">
              <div className="h-3 w-16 bg-border rounded" />
              <div className="h-6 w-12 bg-border rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  const approved = data.byStatus.approved ?? 0;
  const rejected = data.byStatus.rejected ?? 0;
  const modified = data.byStatus.modified ?? 0;
  const expired = data.byStatus.expired ?? 0;
  const approvalRate = data.total > 0 ? (approved / data.total) * 100 : 0;

  const approvalColor =
    approvalRate > 80
      ? 'text-success'
      : approvalRate > 50
        ? 'text-warning'
        : 'text-error';

  const stats = [
    { label: 'Total', value: String(data.total) },
    { label: 'Approved', value: String(approved) },
    { label: 'Rejected', value: String(rejected) },
    { label: 'Modified', value: String(modified) },
    { label: 'Expired', value: String(expired) },
    { label: 'Approval Rate', value: formatPercent(approvalRate, 1), colorClass: approvalColor },
  ];

  return (
    <div className="bg-surface rounded-lg border border-border p-4">
      <div className="flex gap-6">
        {stats.map((stat) => (
          <div key={stat.label} className="flex flex-col">
            <span className="text-xs text-text-tertiary">{stat.label}</span>
            <span
              className={`text-lg font-mono ${stat.colorClass ?? 'text-text-primary'}`}
            >
              {stat.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
