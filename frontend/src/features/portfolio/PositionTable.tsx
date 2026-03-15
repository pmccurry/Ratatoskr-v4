import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { DataTable, LoadingState, EmptyState, ErrorState, PercentValue, ConfirmDialog, DropdownMenu } from '@/components';
import type { Column } from '@/components';
import type { Position } from '@/types/position';
import { formatCurrency } from '@/lib/formatters';
import { STALE, REFRESH } from '@/lib/constants';

type PositionRecord = Position & Record<string, unknown>;

interface PositionTableProps {
  status: 'open' | 'closed';
  onEditPosition?: (position: Position) => void;
}

export function PositionTable({ status, onEditPosition }: PositionTableProps) {
  const queryClient = useQueryClient();

  const [selectedPositionId, setSelectedPositionId] = useState<string | null>(null);
  const [closeDialogOpen, setCloseDialogOpen] = useState(false);
  const [symbolFilter, setSymbolFilter] = useState('');

  const isOpen = status === 'open';

  const { data: positions, isLoading, isError, refetch } = useQuery<Position[]>({
    queryKey: ['portfolio', 'positions', status],
    queryFn: () =>
      api.get(`/portfolio/positions/${status === 'open' ? 'open' : 'closed'}`).then((r) => r.data),
    staleTime: isOpen ? STALE.positionList : 30_000,
    refetchInterval: isOpen ? REFRESH.positions : undefined,
  });

  const selectedPosition = positions?.find((p) => p.id === selectedPositionId) ?? null;

  const handleCloseConfirm = async () => {
    if (!selectedPosition) return;
    await api.post('/signals', {
      symbol: selectedPosition.symbol,
      side: selectedPosition.side === 'long' ? 'sell' : 'buy',
      signalType: 'exit',
      source: 'manual',
    });
    setCloseDialogOpen(false);
    setSelectedPositionId(null);
    queryClient.invalidateQueries({ queryKey: ['portfolio', 'positions'] });
  };

  const openColumns: Column<PositionRecord>[] = [
    { key: 'symbol', label: 'Symbol', sortable: true },
    {
      key: 'side',
      label: 'Side',
      render: (row) => (
        <span className={row.side === 'long' ? 'text-success' : 'text-error'}>
          {(row.side as string).toUpperCase()}
        </span>
      ),
    },
    { key: 'qty', label: 'Qty', type: 'number' },
    { key: 'avgEntryPrice', label: 'Entry', type: 'price' },
    { key: 'currentPrice', label: 'Current', type: 'price' },
    {
      key: 'marketValue',
      label: 'Mkt Value',
      render: (row) => (
        <span className="font-mono">{formatCurrency(row.marketValue as number)}</span>
      ),
    },
    { key: 'unrealizedPnl', label: 'Unrealized', type: 'pnl' },
    {
      key: 'unrealizedPnlPercent',
      label: 'Unreal %',
      render: (row) => <PercentValue value={row.unrealizedPnlPercent as number} colored />,
    },
    { key: 'realizedPnl', label: 'Realized', type: 'pnl' },
    { key: 'totalReturn', label: 'Total Return', type: 'pnl' },
    { key: 'barsHeld', label: 'Bars', type: 'number' },
    {
      key: '_actions',
      label: 'Actions',
      render: (row) => (
        <div className="flex gap-2">
          <DropdownMenu
            trigger={
              <button className="px-2 py-1 text-xs border border-border rounded hover:bg-surface-hover text-text-primary">
                Close ▾
              </button>
            }
            items={[
              {
                label: 'Close All',
                danger: true,
                onClick: () => {
                  setSelectedPositionId(row.id as string);
                  setCloseDialogOpen(true);
                },
              },
              {
                label: 'Close Partial (coming soon)',
                onClick: () => {},
              },
            ]}
          />
          <button
            onClick={() => onEditPosition?.(row as unknown as Position)}
            className="px-2 py-1 text-xs border border-border rounded hover:bg-surface-hover text-text-primary"
          >
            SL/TP
          </button>
        </div>
      ),
    },
  ];

  const closedColumns: Column<PositionRecord>[] = [
    { key: 'symbol', label: 'Symbol', sortable: true },
    {
      key: 'side',
      label: 'Side',
      render: (row) => (
        <span className={row.side === 'long' ? 'text-success' : 'text-error'}>
          {(row.side as string).toUpperCase()}
        </span>
      ),
    },
    { key: 'avgEntryPrice', label: 'Entry', type: 'price' },
    { key: 'currentPrice', label: 'Exit', type: 'price' },
    { key: 'realizedPnl', label: 'PnL', type: 'pnl' },
    {
      key: 'totalReturnPercent',
      label: 'PnL %',
      render: (row) => <PercentValue value={row.totalReturnPercent as number} colored />,
    },
    { key: 'barsHeld', label: 'Bars Held', type: 'number' },
    {
      key: 'closeReason',
      label: 'Close Reason',
      render: (row) => <span>{(row.closeReason as string) || '\u2014'}</span>,
    },
    { key: 'closedAt', label: 'Closed At', type: 'timestamp' },
  ];

  if (isLoading) return <LoadingState rows={8} />;
  if (isError) return <ErrorState message="Failed to load positions" onRetry={refetch} />;

  const filtered = isOpen
    ? (positions ?? [])
    : (positions ?? []).filter(
        (p) => !symbolFilter || p.symbol.toLowerCase().includes(symbolFilter.toLowerCase()),
      );

  const data = filtered as PositionRecord[];

  return (
    <div>
      {!isOpen && (
        <div className="flex flex-wrap gap-3 mb-4">
          <input
            type="text"
            placeholder="Filter by symbol..."
            value={symbolFilter}
            onChange={(e) => setSymbolFilter(e.target.value)}
            className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
          />
        </div>
      )}

      {!data.length ? (
        <EmptyState message={isOpen ? 'No open positions' : 'No closed positions found'} />
      ) : (
        <DataTable
          columns={isOpen ? openColumns : closedColumns}
          data={data}
          emptyMessage={isOpen ? 'No open positions' : 'No closed positions found'}
          keyField="id"
        />
      )}

      <ConfirmDialog
        open={closeDialogOpen}
        title="Close Position"
        message={
          selectedPosition
            ? `Close ${selectedPosition.qty} units of ${selectedPosition.symbol}? This will create a manual exit signal.`
            : ''
        }
        confirmLabel="Close Position"
        variant="danger"
        onConfirm={handleCloseConfirm}
        onCancel={() => {
          setCloseDialogOpen(false);
          setSelectedPositionId(null);
        }}
      />
    </div>
  );
}
