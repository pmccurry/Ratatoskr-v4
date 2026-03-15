import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { DataTable, LoadingState, EmptyState, ErrorState } from '@/components';
import type { Column } from '@/components';
import type { PaperFill } from '@/types/order';
import type { Strategy } from '@/types/strategy';
import { formatCurrency, formatBasisPoints } from '@/lib/formatters';

type FillRecord = PaperFill & Record<string, unknown>;

export function FillTable() {
  const [strategyFilter, setStrategyFilter] = useState('');
  const [symbolFilter, setSymbolFilter] = useState('');
  const [sideFilter, setSideFilter] = useState('');
  const [dateStart, setDateStart] = useState('');
  const [dateEnd, setDateEnd] = useState('');

  const params: Record<string, string> = {};
  if (strategyFilter) params.strategy_id = strategyFilter;
  if (symbolFilter) params.symbol = symbolFilter;
  if (sideFilter) params.side = sideFilter;
  if (dateStart) params.date_start = new Date(dateStart).toISOString();
  if (dateEnd) params.date_end = new Date(dateEnd).toISOString();

  const { data: fills, isLoading, isError, refetch } = useQuery<PaperFill[]>({
    queryKey: ['paper-trading', 'fills', params],
    queryFn: () => api.get('/paper-trading/fills', { params }).then((r) => r.data),
    staleTime: 15_000,
    refetchInterval: 30_000,
  });

  const { data: strategies } = useQuery<Strategy[]>({
    queryKey: ['strategies'],
    queryFn: () => api.get('/strategies').then((r) => r.data?.data ?? r.data),
    staleTime: 60_000,
  });

  const columns: Column<FillRecord>[] = [
    { key: 'filledAt', label: 'Time', type: 'timestamp', sortable: true },
    { key: 'symbol', label: 'Symbol', sortable: true },
    {
      key: 'side',
      label: 'Side',
      render: (row) => (
        <span className={row.side === 'buy' ? 'text-success' : 'text-error'}>
          {(row.side as string).toUpperCase()}
        </span>
      ),
    },
    { key: 'qty', label: 'Qty', type: 'number' },
    { key: 'referencePrice', label: 'Ref Price', type: 'price' },
    { key: 'price', label: 'Fill Price', type: 'price' },
    {
      key: 'fee',
      label: 'Fee',
      render: (row) => (
        <span className="text-text-secondary">{formatCurrency(row.fee as number)}</span>
      ),
    },
    {
      key: 'slippageBps',
      label: 'Slippage',
      render: (row) => <span>{formatBasisPoints(row.slippageBps as number)}</span>,
    },
    {
      key: 'slippageAmount',
      label: 'Slip $',
      render: (row) => {
        const amt = row.slippageAmount as number;
        return (
          <span className={amt > 0 ? 'text-error' : amt < 0 ? 'text-success' : 'text-text-secondary'}>
            {formatCurrency(amt)}
          </span>
        );
      },
    },
    {
      key: 'netValue',
      label: 'Net Value',
      render: (row) => (
        <span className="font-mono">{formatCurrency(row.netValue as number)}</span>
      ),
    },
  ];

  if (isLoading) return <LoadingState rows={8} />;
  if (isError) return <ErrorState message="Failed to load fills" onRetry={refetch} />;

  const data = (fills ?? []) as FillRecord[];

  return (
    <div>
      <div className="flex flex-wrap gap-3 mb-4">
        <select
          value={strategyFilter}
          onChange={(e) => setStrategyFilter(e.target.value)}
          className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
        >
          <option value="">All Strategies</option>
          {(strategies ?? []).map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Symbol..."
          value={symbolFilter}
          onChange={(e) => setSymbolFilter(e.target.value)}
          className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
        />
        <select
          value={sideFilter}
          onChange={(e) => setSideFilter(e.target.value)}
          className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
        >
          <option value="">All Sides</option>
          <option value="buy">Buy</option>
          <option value="sell">Sell</option>
        </select>
        <input
          type="date"
          value={dateStart}
          onChange={(e) => setDateStart(e.target.value)}
          className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
          placeholder="Start date"
        />
        <input
          type="date"
          value={dateEnd}
          onChange={(e) => setDateEnd(e.target.value)}
          className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
          placeholder="End date"
        />
      </div>

      {!data.length ? (
        <EmptyState message="No fills found" />
      ) : (
        <DataTable
          columns={columns}
          data={data}
          emptyMessage="No fills found"
          keyField="id"
        />
      )}
    </div>
  );
}
