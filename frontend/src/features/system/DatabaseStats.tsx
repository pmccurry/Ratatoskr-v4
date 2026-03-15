import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { DataTable, LoadingState, EmptyState, ErrorState } from '@/components';
import type { Column } from '@/components/DataTable';

export function DatabaseStats() {
  const { data: stats, isLoading, isError, refetch } = useQuery<Record<string, unknown>[]>({
    queryKey: ['observability', 'database', 'stats'],
    queryFn: () => api.get('/observability/database/stats').then((r) => r.data),
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

  if (isLoading) return <LoadingState rows={4} />;
  if (isError) return <ErrorState message="Failed to load database stats" onRetry={refetch} />;
  if (!stats || stats.length === 0) return <EmptyState message="No database statistics available" />;

  const columns: Column<Record<string, unknown>>[] = [
    { key: 'tableName', label: 'Table', sortable: true },
    {
      key: 'rowCount',
      label: 'Rows',
      sortable: true,
      type: 'number',
    },
    {
      key: 'estimatedSize',
      label: 'Est. Size',
      sortable: true,
    },
  ];

  return (
    <DataTable<Record<string, unknown>>
      columns={columns}
      data={stats}
      keyField="tableName"
    />
  );
}
