import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getStrategyBacktests } from './backtestApi';
import type { BacktestRun } from './backtestApi';
import { formatPnl, formatPercent, formatDateTime } from '@/lib/formatters';
import { DataTable, LoadingState, ErrorState, EmptyState } from '@/components';
import type { Column } from '@/components';

type BacktestRow = BacktestRun & Record<string, unknown>;

interface BacktestResultsListProps {
  strategyId: string;
}

export function BacktestResultsList({ strategyId }: BacktestResultsListProps) {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const { data: response, isLoading, isError, refetch } = useQuery<{ data: BacktestRun[]; total: number }>({
    queryKey: ['backtests', strategyId, page, pageSize],
    queryFn: () => getStrategyBacktests(strategyId, page, pageSize).then((r) => r.data),
    staleTime: 30_000,
  });

  const data = response?.data ?? [];
  const total = response?.total ?? 0;

  const columns: Column<BacktestRow>[] = [
    {
      key: 'createdAt',
      label: 'Date',
      sortable: true,
      render: (row: BacktestRow) => (
        <button
          className="text-accent hover:underline font-medium text-left"
          onClick={() => navigate(`/backtests/${row.id}`)}
        >
          {formatDateTime(row.createdAt)}
        </button>
      ),
    },
    {
      key: 'timeframe',
      label: 'Timeframe',
      render: (row: BacktestRow) => (
        <span className="font-mono text-text-primary">{row.timeframe}</span>
      ),
    },
    {
      key: 'startDate',
      label: 'Period',
      render: (row: BacktestRow) => (
        <span className="text-text-secondary text-xs">
          {row.startDate} to {row.endDate}
        </span>
      ),
    },
    {
      key: 'totalTrades',
      label: 'Trades',
      type: 'number',
      sortable: true,
    },
    {
      key: 'netPnl',
      label: 'Net PnL',
      sortable: true,
      render: (row: BacktestRow) => {
        const pnl = row.metrics?.netPnl ?? row.metrics?.net_pnl ?? null;
        if (pnl == null) return <span className="text-text-tertiary">--</span>;
        const val = Number(pnl);
        return (
          <span className={val >= 0 ? 'text-success font-mono' : 'text-error font-mono'}>
            {formatPnl(val)}
          </span>
        );
      },
    },
    {
      key: 'winRate',
      label: 'Win Rate',
      sortable: true,
      render: (row: BacktestRow) => {
        const wr = row.metrics?.winRate ?? row.metrics?.win_rate ?? null;
        if (wr == null) return <span className="text-text-tertiary">--</span>;
        return <span className="font-mono">{formatPercent(Number(wr))}</span>;
      },
    },
    {
      key: 'sharpe',
      label: 'Sharpe',
      sortable: true,
      render: (row: BacktestRow) => {
        const sr = row.metrics?.sharpeRatio ?? row.metrics?.sharpe_ratio ?? null;
        if (sr == null) return <span className="text-text-tertiary">--</span>;
        return <span className="font-mono">{Number(sr).toFixed(2)}</span>;
      },
    },
    {
      key: 'maxDrawdown',
      label: 'Max DD',
      sortable: true,
      render: (row: BacktestRow) => {
        const dd = row.metrics?.maxDrawdownPct ?? row.metrics?.max_drawdown_pct ?? null;
        if (dd == null) return <span className="text-text-tertiary">--</span>;
        const val = Number(dd);
        return (
          <span className={val > 10 ? 'text-error font-mono' : 'text-warning font-mono'}>
            {formatPercent(-Math.abs(val))}
          </span>
        );
      },
    },
    {
      key: 'status',
      label: 'Status',
      type: 'status',
    },
  ];

  if (isLoading) return <LoadingState rows={5} />;

  if (isError) return <ErrorState message="Failed to load backtest history" onRetry={() => refetch()} />;

  if (data.length === 0) return <EmptyState message="No backtests have been run for this strategy" />;

  const tableData: BacktestRow[] = data as BacktestRow[];

  return (
    <DataTable<BacktestRow>
      columns={columns}
      data={tableData}
      page={page}
      pageSize={pageSize}
      total={total}
      onPageChange={setPage}
      onPageSizeChange={(size) => {
        setPageSize(size);
        setPage(1);
      }}
    />
  );
}
