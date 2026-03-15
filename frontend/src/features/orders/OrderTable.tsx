import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { DataTable, LoadingState, EmptyState, ErrorState } from '@/components';
import type { Column } from '@/components';
import type { PaperOrder } from '@/types/order';
import type { Strategy } from '@/types/strategy';

type OrderRecord = PaperOrder & Record<string, unknown>;

export function OrderTable() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [strategyFilter, setStrategyFilter] = useState('');
  const [symbolFilter, setSymbolFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [marketFilter, setMarketFilter] = useState('');
  const [selectedOrder, setSelectedOrder] = useState<PaperOrder | null>(null);

  const params: Record<string, string | number> = { page, pageSize };
  if (strategyFilter) params.strategy_id = strategyFilter;
  if (symbolFilter) params.symbol = symbolFilter;
  if (statusFilter) params.status = statusFilter;
  if (marketFilter) params.market = marketFilter;

  const { data: response, isLoading, isError, refetch } = useQuery<{ data: PaperOrder[]; total: number }>({
    queryKey: ['paper-trading', 'orders', params],
    queryFn: () => api.get('/paper-trading/orders', { params }).then((r) => r.data),
    staleTime: 15_000,
    refetchInterval: 30_000,
  });

  const { data: strategies } = useQuery<Strategy[]>({
    queryKey: ['strategies'],
    queryFn: () => api.get('/strategies').then((r) => r.data?.data ?? r.data),
    staleTime: 60_000,
  });

  const orders = response?.data ?? [];
  const serverTotal = response?.total ?? 0;

  const columns: Column<OrderRecord>[] = [
    { key: 'submittedAt', label: 'Time', type: 'timestamp', sortable: true },
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
    { key: 'orderType', label: 'Type' },
    { key: 'requestedQty', label: 'Qty', type: 'number' },
    { key: 'filledAvgPrice', label: 'Price', type: 'price' },
    { key: 'status', label: 'Status', type: 'status' },
    {
      key: 'strategyId',
      label: 'Strategy',
      render: (row) => (
        <span className="font-mono text-text-secondary">
          {(row.strategyId as string).slice(0, 8)}
        </span>
      ),
    },
    {
      key: 'id',
      label: '',
      render: (row) => (
        <button
          onClick={() => setSelectedOrder(row as unknown as PaperOrder)}
          className="text-accent hover:text-accent/80 text-xs"
        >
          Details
        </button>
      ),
    },
  ];

  if (isLoading) return <LoadingState rows={8} />;
  if (isError) return <ErrorState message="Failed to load orders" onRetry={refetch} />;

  const data = orders as OrderRecord[];

  return (
    <div>
      <div className="flex flex-wrap gap-3 mb-4">
        <select
          value={strategyFilter}
          onChange={(e) => { setStrategyFilter(e.target.value); setPage(1); }}
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
          onChange={(e) => { setSymbolFilter(e.target.value); setPage(1); }}
          className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
        />
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="submitted">Submitted</option>
          <option value="filled">Filled</option>
          <option value="partial">Partial</option>
          <option value="rejected">Rejected</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <select
          value={marketFilter}
          onChange={(e) => { setMarketFilter(e.target.value); setPage(1); }}
          className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
        >
          <option value="">All Markets</option>
          <option value="equities">Equities</option>
          <option value="forex">Forex</option>
          <option value="options">Options</option>
        </select>
      </div>

      {!data.length ? (
        <EmptyState message="No orders found" />
      ) : (
        <DataTable
          columns={columns}
          data={data}
          emptyMessage="No orders found"
          keyField="id"
          page={page}
          pageSize={pageSize}
          total={serverTotal}
          onPageChange={setPage}
          onPageSizeChange={(size) => { setPageSize(size); setPage(1); }}
        />
      )}

      {selectedOrder && (
        <div className="bg-background rounded p-4 mt-4 text-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-medium text-text-primary">Order Details</span>
            <button
              onClick={() => setSelectedOrder(null)}
              className="text-text-secondary hover:text-text-primary"
            >
              Close
            </button>
          </div>
          <div className="grid grid-cols-2 gap-2 text-text-secondary">
            <div>Order ID: <span className="text-text-primary font-mono">{selectedOrder.id}</span></div>
            <div>Signal ID: <span className="text-text-primary font-mono">{selectedOrder.signalId}</span></div>
            <div>Risk Decision ID: <span className="text-text-primary font-mono">{selectedOrder.riskDecisionId}</span></div>
            <div>Execution Mode: <span className="text-text-primary">{selectedOrder.executionMode}</span></div>
            <div>Broker Order ID: <span className="text-text-primary font-mono">{selectedOrder.brokerOrderId ?? '—'}</span></div>
            <div>Broker Account ID: <span className="text-text-primary font-mono">{selectedOrder.brokerAccountId ?? '—'}</span></div>
            <div>Signal Type: <span className="text-text-primary">{selectedOrder.signalType}</span></div>
            <div>Contract Multiplier: <span className="text-text-primary">{selectedOrder.contractMultiplier}</span></div>
            <div>Filled Qty: <span className="text-text-primary">{selectedOrder.filledQty}</span></div>
            <div>Filled At: <span className="text-text-primary">{selectedOrder.filledAt ?? '—'}</span></div>
            <div>Rejection Reason: <span className="text-text-primary">{selectedOrder.rejectionReason ?? '—'}</span></div>
            <div>Created At: <span className="text-text-primary">{selectedOrder.createdAt}</span></div>
          </div>
        </div>
      )}
    </div>
  );
}
