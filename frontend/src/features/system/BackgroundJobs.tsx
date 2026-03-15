import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { DataTable, LoadingState, EmptyState, ErrorState, StatusPill, TimeAgo } from '@/components';
import type { Column } from '@/components/DataTable';

export function BackgroundJobs() {
  const { data: jobs, isLoading, isError, refetch } = useQuery<Record<string, unknown>[]>({
    queryKey: ['observability', 'jobs'],
    queryFn: () => api.get('/observability/jobs').then((r) => r.data),
    staleTime: 10_000,
    refetchInterval: 30_000,
  });

  if (isLoading) return <LoadingState rows={4} />;
  if (isError) return <ErrorState message="Failed to load background jobs" onRetry={refetch} />;
  if (!jobs || jobs.length === 0) return <EmptyState message="No background jobs found" />;

  const columns: Column<Record<string, unknown>>[] = [
    { key: 'name', label: 'Name', sortable: true },
    {
      key: 'lastRun',
      label: 'Last Run',
      sortable: true,
      render: (row) =>
        row.lastRun ? <TimeAgo value={row.lastRun as string} /> : <span className="text-text-tertiary">—</span>,
    },
    {
      key: 'nextRun',
      label: 'Next Run',
      sortable: true,
      render: (row) =>
        row.nextRun ? <TimeAgo value={row.nextRun as string} /> : <span className="text-text-tertiary">—</span>,
    },
    {
      key: 'status',
      label: 'Status',
      render: (row) => <StatusPill status={row.status as string} />,
    },
    {
      key: 'durationMs',
      label: 'Duration',
      render: (row) =>
        row.durationMs != null ? (
          <span className="font-mono">{Number(row.durationMs).toLocaleString()} ms</span>
        ) : (
          <span className="text-text-tertiary">—</span>
        ),
    },
  ];

  return (
    <DataTable<Record<string, unknown>>
      columns={columns}
      data={jobs}
      keyField="name"
    />
  );
}
