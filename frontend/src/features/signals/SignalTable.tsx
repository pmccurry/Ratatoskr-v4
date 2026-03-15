import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { formatPercent } from '@/lib/formatters';
import { DataTable, LoadingState, EmptyState, ErrorState } from '@/components';
import type { Column } from '@/components';
import type { Signal } from '@/types/signal';
import type { Strategy } from '@/types/strategy';
import { SignalDetail } from './SignalDetail';

type SignalRow = Signal & Record<string, unknown>;

export function SignalTable() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [strategyFilter, setStrategyFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [symbolFilter, setSymbolFilter] = useState('');
  const [signalTypeFilter, setSignalTypeFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [selectedSignalId, setSelectedSignalId] = useState<string | null>(null);

  const params: Record<string, string | number> = { page, pageSize };
  if (strategyFilter) params.strategy_id = strategyFilter;
  if (statusFilter) params.status = statusFilter;
  if (symbolFilter) params.symbol = symbolFilter;
  if (signalTypeFilter) params.signal_type = signalTypeFilter;
  if (sourceFilter) params.source = sourceFilter;

  const { data: response, isLoading, isError, refetch } = useQuery<{ data: Signal[]; total: number }>({
    queryKey: ['signals', 'list', params],
    queryFn: () => api.get('/signals', { params }).then((r) => r.data),
    staleTime: 10_000,
    refetchInterval: 10_000,
  });

  const { data: strategies } = useQuery<Strategy[]>({
    queryKey: ['strategies'],
    queryFn: () => api.get('/strategies').then((r) => r.data?.data ?? r.data),
    staleTime: 60_000,
  });

  const data = response?.data ?? [];
  const serverTotal = response?.total ?? 0;

  const columns: Column<SignalRow>[] = [
    {
      key: 'ts',
      label: 'Time',
      type: 'timestamp',
      sortable: true,
    },
    {
      key: 'symbol',
      label: 'Symbol',
      sortable: true,
      render: (row: SignalRow) => (
        <button
          className="text-accent hover:underline font-medium"
          onClick={() =>
            setSelectedSignalId(
              selectedSignalId === row.id ? null : row.id,
            )
          }
        >
          {row.symbol as string}
        </button>
      ),
    },
    {
      key: 'side',
      label: 'Side',
      render: (row: SignalRow) => (
        <span
          className={
            row.side === 'buy'
              ? 'text-success font-medium'
              : 'text-error font-medium'
          }
        >
          {(row.side as string).toUpperCase()}
        </span>
      ),
    },
    {
      key: 'signalType',
      label: 'Type',
    },
    {
      key: 'strategyId',
      label: 'Strategy',
      render: (row: SignalRow) => (
        <span className="font-mono text-text-secondary" title={row.strategyId as string}>
          {(row.strategyId as string).slice(0, 8)}
        </span>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      type: 'status',
    },
    {
      key: 'confidence',
      label: 'Confidence',
      render: (row: SignalRow) => (
        <span className="font-mono">
          {formatPercent((row.confidence as number) * 100, 1)}
        </span>
      ),
    },
    {
      key: 'source',
      label: 'Source',
    },
  ];

  const selectedSignal =
    selectedSignalId && data.length
      ? data.find((s) => s.id === selectedSignalId)
      : null;

  const tableData: SignalRow[] = data as SignalRow[];

  return (
    <div>
      <div className="flex flex-wrap gap-3 mb-4">
        <select
          value={strategyFilter}
          onChange={(e) => {
            setStrategyFilter(e.target.value);
            setPage(1);
          }}
          className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
        >
          <option value="">All Strategies</option>
          {(strategies ?? []).map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="modified">Modified</option>
          <option value="expired">Expired</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <input
          type="text"
          placeholder="Symbol..."
          value={symbolFilter}
          onChange={(e) => {
            setSymbolFilter(e.target.value);
            setPage(1);
          }}
          className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
        />
        <select
          value={signalTypeFilter}
          onChange={(e) => {
            setSignalTypeFilter(e.target.value);
            setPage(1);
          }}
          className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
        >
          <option value="">All Types</option>
          <option value="entry">Entry</option>
          <option value="exit">Exit</option>
        </select>
        <select
          value={sourceFilter}
          onChange={(e) => {
            setSourceFilter(e.target.value);
            setPage(1);
          }}
          className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
        >
          <option value="">All Sources</option>
          <option value="strategy">Strategy</option>
          <option value="manual">Manual</option>
          <option value="safety">Safety</option>
          <option value="system">System</option>
        </select>
      </div>

      {isLoading && <LoadingState rows={5} />}

      {isError && (
        <ErrorState message="Failed to load signals" onRetry={() => refetch()} />
      )}

      {!isLoading && !isError && tableData.length === 0 && (
        <EmptyState message="No signals found" />
      )}

      {!isLoading && !isError && tableData.length > 0 && (
        <DataTable<SignalRow>
          columns={columns}
          data={tableData}
          page={page}
          pageSize={pageSize}
          total={serverTotal}
          onPageChange={setPage}
          onPageSizeChange={(size) => {
            setPageSize(size);
            setPage(1);
          }}
        />
      )}

      {selectedSignal && (
        <div className="mt-4">
          <div className="text-xs text-text-tertiary mb-2">
            Payload for signal {selectedSignal.id.slice(0, 8)}
          </div>
          <SignalDetail payloadJson={selectedSignal.payloadJson} />
        </div>
      )}
    </div>
  );
}
