import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { DataTable, LoadingState, ErrorState, PercentValue, PnlValue } from '@/components';
import type { Column } from '@/components';
import type { BacktestTrade } from './backtestApi';
import { getBacktestTrades } from './backtestApi';

type TradeRecord = BacktestTrade & Record<string, unknown>;

const EXIT_REASON_LABELS: Record<string, string> = {
  SL: 'Stop Loss',
  TP: 'Take Profit',
  signal: 'Signal',
  time_exit: 'Time',
  end_of_data: 'EOD',
};

function ExitReasonBadge({ reason }: { reason: string | null }) {
  if (!reason) return <span className="text-text-tertiary">--</span>;
  const label = EXIT_REASON_LABELS[reason] ?? reason;
  return (
    <span className="inline-block px-2 py-0.5 text-xs rounded bg-surface-hover text-text-secondary border border-border">
      {label}
    </span>
  );
}

export function BacktestTradeTable({ backtestId }: { backtestId: string }) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  const { data: response, isLoading, isError, refetch } = useQuery<{ data: BacktestTrade[]; total: number }>({
    queryKey: ['backtesting', backtestId, 'trades', page, pageSize],
    queryFn: () => getBacktestTrades(backtestId, page, pageSize).then((r) => r.data),
    staleTime: 30_000,
  });

  // The API interceptor unwraps the {data: ...} envelope, so the response
  // may be the inner trades array directly or a {data: [...], total} object.
  // Handle both shapes defensively, matching the pattern in OrderTable.
  const trades = Array.isArray(response) ? response : (response?.data ?? []);
  const serverTotal = Array.isArray(response) ? 0 : (response?.total ?? 0);

  const columns: Column<TradeRecord>[] = [
    { key: 'symbol', label: 'Symbol', sortable: true },
    {
      key: 'side',
      label: 'Side',
      render: (row) => (
        <span className={row.side === 'long' ? 'text-success' : 'text-error'}>
          {row.side === 'long' ? 'LONG' : 'SHORT'}
        </span>
      ),
    },
    { key: 'entryTime', label: 'Entry Time', type: 'timestamp' },
    { key: 'entryPrice', label: 'Entry Price', type: 'price' },
    { key: 'exitTime', label: 'Exit Time', type: 'timestamp' },
    { key: 'exitPrice', label: 'Exit Price', type: 'price' },
    { key: 'pnl', label: 'PnL', type: 'pnl', sortable: true },
    {
      key: 'pnlPercent',
      label: 'PnL %',
      sortable: true,
      render: (row) => (
        row.pnlPercent != null
          ? <PercentValue value={row.pnlPercent as number} colored />
          : <span className="text-text-tertiary">--</span>
      ),
    },
    {
      key: 'holdBars',
      label: 'Duration',
      sortable: true,
      render: (row) => (
        row.holdBars != null
          ? <span className="font-mono">{row.holdBars} bars</span>
          : <span className="text-text-tertiary">--</span>
      ),
    },
    {
      key: 'exitReason',
      label: 'Exit Reason',
      render: (row) => <ExitReasonBadge reason={row.exitReason as string | null} />,
    },
  ];

  if (isLoading) return <LoadingState rows={8} />;
  if (isError) return <ErrorState message="Failed to load backtest trades" onRetry={refetch} />;

  const totalPnl = trades.reduce((sum, t) => sum + (t.pnl ?? 0), 0);
  const tradeCount = serverTotal || trades.length;

  return (
    <div>
      <DataTable
        columns={columns}
        data={(trades as TradeRecord[])}
        emptyMessage="No trades in this backtest"
        keyField="id"
        page={page}
        pageSize={pageSize}
        total={serverTotal}
        onPageChange={setPage}
        onPageSizeChange={(size) => { setPageSize(size); setPage(1); }}
      />
      {trades.length > 0 && (
        <div className="flex items-center gap-4 mt-2 px-4 py-2 text-sm text-text-secondary bg-surface rounded-b-lg border border-t-0 border-border">
          <span>{tradeCount} trades</span>
          <span>Net PnL: <PnlValue value={totalPnl} /></span>
        </div>
      )}
    </div>
  );
}
