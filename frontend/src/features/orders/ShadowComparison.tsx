import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { SectionHeader, DataTable, PnlValue, LoadingState, EmptyState, ErrorState } from '@/components';
import type { Column } from '@/components';
import { formatCurrency } from '@/lib/formatters';

interface ShadowPosition {
  id: string;
  strategyId: string;
  symbol: string;
  side: string;
  entryPrice: number;
  currentPrice: number | null;
  exitPrice: number | null;
  unrealizedPnl: number;
  realizedPnl: number;
  status: string;
  closeReason: string | null;
}

interface ShadowComparisonEntry {
  strategyId: string;
  strategyName: string;
  realTrades: number;
  realPnl: number;
  shadowTrades: number;
  shadowPnl: number;
  blockedSignals: number;
  missedPnl: number;
}

type ShadowPositionRecord = ShadowPosition & Record<string, unknown>;
type ComparisonRecord = ShadowComparisonEntry & Record<string, unknown>;

export function ShadowComparison() {
  const {
    data: positions,
    isLoading: posLoading,
    isError: posError,
    refetch: posRefetch,
  } = useQuery<ShadowPosition[]>({
    queryKey: ['paper-trading', 'shadow', 'positions'],
    queryFn: () => api.get('/paper-trading/shadow/positions').then((r) => r.data),
    staleTime: 15_000,
    refetchInterval: 30_000,
  });

  const {
    data: comparison,
    isLoading: cmpLoading,
    isError: cmpError,
    refetch: cmpRefetch,
  } = useQuery<ShadowComparisonEntry[]>({
    queryKey: ['paper-trading', 'shadow', 'comparison'],
    queryFn: () => api.get('/paper-trading/shadow/comparison').then((r) => r.data),
    staleTime: 15_000,
    refetchInterval: 30_000,
  });

  const positionColumns: Column<ShadowPositionRecord>[] = [
    {
      key: 'strategyId',
      label: 'Strategy',
      render: (row) => (
        <span className="font-mono text-text-secondary">
          {(row.strategyId as string).slice(0, 8)}
        </span>
      ),
    },
    { key: 'symbol', label: 'Symbol' },
    {
      key: 'side',
      label: 'Side',
      render: (row) => (
        <span className={row.side === 'buy' ? 'text-success' : 'text-error'}>
          {(row.side as string).toUpperCase()}
        </span>
      ),
    },
    { key: 'entryPrice', label: 'Entry', type: 'price' },
    {
      key: 'currentPrice',
      label: 'Current/Exit',
      render: (row) => {
        const price = row.exitPrice != null ? row.exitPrice : row.currentPrice;
        return price != null ? <span className="font-mono">{formatCurrency(price as number)}</span> : <span>—</span>;
      },
    },
    {
      key: 'unrealizedPnl',
      label: 'PnL',
      render: (row) => {
        const isClosed = row.status === 'closed';
        const value = isClosed ? (row.realizedPnl as number) : (row.unrealizedPnl as number);
        return <PnlValue value={value} />;
      },
    },
    { key: 'status', label: 'Status', type: 'status' },
    {
      key: 'closeReason',
      label: 'Close Reason',
      render: (row) => <span>{(row.closeReason as string | null) ?? '—'}</span>,
    },
  ];

  const comparisonColumns: Column<ComparisonRecord>[] = [
    { key: 'strategyName', label: 'Strategy' },
    { key: 'realTrades', label: 'Real Trades', type: 'number' },
    { key: 'realPnl', label: 'Real PnL', type: 'pnl' },
    { key: 'shadowTrades', label: 'Shadow Trades', type: 'number' },
    { key: 'shadowPnl', label: 'Shadow PnL', type: 'pnl' },
    { key: 'blockedSignals', label: 'Blocked', type: 'number' },
    {
      key: 'missedPnl',
      label: 'Missed PnL',
      render: (row) => (
        <PnlValue
          value={row.missedPnl as number}
          className="bg-warning/10 px-2 py-0.5 rounded"
        />
      ),
    },
  ];

  const isLoading = posLoading || cmpLoading;

  if (isLoading) return <LoadingState rows={6} />;

  return (
    <div className="space-y-8">
      <div>
        <SectionHeader title="Shadow Positions" />
        {posError ? (
          <ErrorState message="Failed to load shadow positions" onRetry={posRefetch} />
        ) : !positions?.length ? (
          <EmptyState message="No shadow positions" />
        ) : (
          <DataTable
            columns={positionColumns}
            data={positions as ShadowPositionRecord[]}
            emptyMessage="No shadow positions"
            keyField="id"
          />
        )}
      </div>

      <div>
        <SectionHeader title="Real vs Shadow Performance" />
        {cmpError ? (
          <ErrorState message="Failed to load shadow comparison" onRetry={cmpRefetch} />
        ) : !comparison?.length ? (
          <EmptyState message="No comparison data available" />
        ) : (
          <DataTable
            columns={comparisonColumns}
            data={comparison as ComparisonRecord[]}
            emptyMessage="No comparison data"
            keyField="strategyId"
          />
        )}
      </div>
    </div>
  );
}
