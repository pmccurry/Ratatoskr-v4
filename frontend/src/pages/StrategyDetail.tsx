import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AreaChart, Area, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';
import api from '@/lib/api';
import { STALE, REFRESH, COLORS } from '@/lib/constants';
import { formatCurrency, formatPercent, formatPnl, formatDateTime } from '@/lib/formatters';
import { PageContainer } from '@/components/PageContainer';
import {
  StatusPill, StatCard, CardGrid, TabContainer, DataTable, LoadingState,
  EmptyState, ErrorState, PercentValue, ChartContainer,
  ConfirmDialog,
} from '@/components';
import type { Column } from '@/components';
import type { StrategyDetail as StrategyDetailType, StrategyEvaluation } from '@/types/strategy';
import type { Position } from '@/types/position';
import { BacktestForm } from '@/features/backtesting/BacktestForm';
import { BacktestResultsList } from '@/features/backtesting/BacktestResultsList';

type PositionRecord = Position & Record<string, unknown>;
type EvalRecord = StrategyEvaluation & Record<string, unknown>;

interface PerformanceMetrics {
  totalPnl: number;
  winRate: number;
  totalTrades: number;
  profitFactor: number;
  avgWinner: number;
  avgLoser: number;
  riskReward: number;
  maxDrawdown: number;
  sharpeRatio: number;
  avgHoldBars: number;
  dividendIncome: number;
}

interface ClosedTrade {
  id: string;
  symbol: string;
  side: string;
  entryPrice: number;
  exitPrice: number;
  realizedPnl: number;
  totalReturnPercent: number;
  barsHeld: number;
  closedAt: string;
  closeReason: string;
}
type TradeRecord = ClosedTrade & Record<string, unknown>;

interface StrategyVersion {
  version: number;
  createdAt: string;
  changes: string[];
}

const TABS = [
  { key: 'performance', label: 'Performance' },
  { key: 'positions', label: 'Open Positions' },
  { key: 'signals', label: 'Signals' },
  { key: 'config', label: 'Config' },
  { key: 'evaluations', label: 'Evaluation Log' },
  { key: 'backtest', label: 'Backtest' },
  { key: 'backtestResults', label: 'Results' },
];

export default function StrategyDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [closePositionId, setClosePositionId] = useState<string | null>(null);
  const [editPositionId, setEditPositionId] = useState<string | null>(null);
  const [expandedEvalId, setExpandedEvalId] = useState<string | null>(null);
  const [slValue, setSlValue] = useState('');
  const [tpValue, setTpValue] = useState('');

  const { data: strategy, isLoading, isError, refetch } = useQuery<StrategyDetailType>({
    queryKey: ['strategies', id],
    queryFn: () => api.get(`/strategies/${id}`).then((r) => r.data),
    staleTime: STALE.strategyList,
  });

  const { data: metrics } = useQuery<PerformanceMetrics>({
    queryKey: ['portfolio', 'metrics', id],
    queryFn: () => api.get(`/portfolio/metrics/${id}`).then((r) => r.data),
    staleTime: STALE.portfolioSummary,
    enabled: !!id,
  });

  const { data: equityData } = useQuery<Array<{ timestamp: string; equity: number }>>({
    queryKey: ['portfolio', 'equity-curve', id],
    queryFn: () => api.get(`/portfolio/equity-curve?strategyId=${id}`).then((r) => r.data),
    staleTime: STALE.portfolioSummary,
    enabled: !!id,
  });

  const { data: positions } = useQuery<Position[]>({
    queryKey: ['portfolio', 'positions', 'open', id],
    queryFn: () => api.get(`/portfolio/positions/open?strategyId=${id}`).then((r) => r.data),
    staleTime: STALE.positionList,
    refetchInterval: REFRESH.positions,
    enabled: !!id,
  });

  const { data: closedTrades } = useQuery<ClosedTrade[]>({
    queryKey: ['portfolio', 'pnl', 'realized', id],
    queryFn: () => api.get(`/portfolio/pnl/realized?strategyId=${id}`).then((r) => r.data),
    staleTime: STALE.portfolioSummary,
    enabled: !!id,
  });

  const { data: signals } = useQuery<Array<Record<string, unknown>>>({
    queryKey: ['signals', { strategyId: id }],
    queryFn: () => api.get(`/signals?strategyId=${id}`).then((r) => r.data),
    staleTime: STALE.signalList,
    refetchInterval: REFRESH.signals,
    enabled: !!id,
  });

  const { data: versions } = useQuery<StrategyVersion[]>({
    queryKey: ['strategies', id, 'versions'],
    queryFn: () => api.get(`/strategies/${id}/versions`).then((r) => r.data),
    staleTime: STALE.strategyList,
    enabled: !!id,
  });

  const { data: evaluations } = useQuery<StrategyEvaluation[]>({
    queryKey: ['strategies', id, 'evaluations'],
    queryFn: () => api.get(`/strategies/${id}/evaluations`).then((r) => r.data),
    staleTime: STALE.strategyList,
    refetchInterval: REFRESH.strategyList,
    enabled: !!id,
  });

  const pauseMutation = useMutation({
    mutationFn: () => api.post(`/strategies/${id}/pause`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['strategies', id] }),
  });

  const enableMutation = useMutation({
    mutationFn: () => api.post(`/strategies/${id}/enable`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['strategies', id] }),
  });

  const disableMutation = useMutation({
    mutationFn: () => api.post(`/strategies/${id}/disable`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['strategies', id] }),
  });

  const closePositionMutation = useMutation({
    mutationFn: (position: Position) =>
      api.post('/signals', {
        symbol: position.symbol,
        side: position.side === 'long' ? 'sell' : 'buy',
        signalType: 'exit',
        source: 'manual',
      }),
    onSuccess: () => {
      setClosePositionId(null);
      queryClient.invalidateQueries({ queryKey: ['portfolio', 'positions'] });
    },
  });

  const saveOverrideMutation = useMutation({
    mutationFn: ({ posId, sl, tp }: { posId: string; sl: number | null; tp: number | null }) =>
      api.put(`/portfolio/positions/${posId}/overrides`, { stopLoss: sl, takeProfit: tp }),
    onSuccess: () => {
      setEditPositionId(null);
      queryClient.invalidateQueries({ queryKey: ['portfolio', 'positions'] });
    },
  });

  if (isLoading) return <PageContainer><LoadingState rows={8} /></PageContainer>;
  if (isError || !strategy) return <PageContainer><ErrorState message="Failed to load strategy" onRetry={refetch} /></PageContainer>;

  const positionsData = (positions ?? []) as PositionRecord[];
  const selectedClosePos = positionsData.find((p) => p.id === closePositionId) ?? null;

  const positionColumns: Column<PositionRecord>[] = [
    { key: 'symbol', label: 'Symbol', sortable: true },
    {
      key: 'side', label: 'Side',
      render: (row) => (
        <span className={row.side === 'long' ? 'text-success' : 'text-error'}>
          {(row.side as string).toUpperCase()}
        </span>
      ),
    },
    { key: 'qty', label: 'Qty', type: 'number' },
    { key: 'avgEntryPrice', label: 'Entry', type: 'price' },
    { key: 'currentPrice', label: 'Current', type: 'price' },
    { key: 'unrealizedPnl', label: 'Unrealized', type: 'pnl' },
    {
      key: 'unrealizedPnlPercent', label: 'Unreal %',
      render: (row) => <PercentValue value={row.unrealizedPnlPercent as number} colored />,
    },
    { key: 'barsHeld', label: 'Bars', type: 'number' },
    {
      key: '_actions', label: 'Actions',
      render: (row) => (
        <div className="flex gap-2">
          <button
            onClick={() => setClosePositionId(row.id as string)}
            className="px-2 py-1 text-xs border border-border rounded hover:bg-surface-hover text-text-primary"
          >Close</button>
          <button
            onClick={() => {
              setEditPositionId(row.id as string);
              setSlValue('');
              setTpValue('');
            }}
            className="px-2 py-1 text-xs border border-border rounded hover:bg-surface-hover text-text-primary"
          >SL/TP</button>
        </div>
      ),
    },
  ];

  const tradeColumns: Column<TradeRecord>[] = [
    { key: 'symbol', label: 'Symbol', sortable: true },
    { key: 'side', label: 'Side' },
    { key: 'entryPrice', label: 'Entry', type: 'price' },
    { key: 'exitPrice', label: 'Exit', type: 'price' },
    { key: 'realizedPnl', label: 'PnL', type: 'pnl' },
    {
      key: 'totalReturnPercent', label: 'Return %',
      render: (row) => <PercentValue value={row.totalReturnPercent as number} colored />,
    },
    { key: 'barsHeld', label: 'Bars', type: 'number' },
    { key: 'closeReason', label: 'Reason' },
    { key: 'closedAt', label: 'Closed', type: 'timestamp' },
  ];

  const signalColumns: Column<Record<string, unknown>>[] = [
    { key: 'createdAt', label: 'Time', type: 'timestamp', sortable: true },
    { key: 'symbol', label: 'Symbol' },
    { key: 'side', label: 'Side' },
    { key: 'signalType', label: 'Type' },
    { key: 'status', label: 'Status', type: 'status' },
    { key: 'confidence', label: 'Confidence', type: 'number' },
    { key: 'source', label: 'Source' },
  ];

  const evalColumns: Column<EvalRecord>[] = [
    {
      key: 'evaluatedAt', label: 'Time', type: 'timestamp', sortable: true,
      render: (row) => (
        <button
          onClick={() => setExpandedEvalId(expandedEvalId === (row.id as string) ? null : (row.id as string))}
          className="text-left text-accent hover:underline"
        >
          {formatDateTime(row.evaluatedAt as string)} {expandedEvalId === (row.id as string) ? '▾' : '▸'}
        </button>
      ),
    },
    { key: 'symbolsEvaluated', label: 'Symbols', type: 'number' },
    { key: 'signalsEmitted', label: 'Signals', type: 'number' },
    { key: 'exitsTriggered', label: 'Exits', type: 'number' },
    {
      key: 'durationMs', label: 'Duration',
      render: (row) => <span className="font-mono">{row.durationMs as number}ms</span>,
    },
    { key: 'status', label: 'Status', type: 'status' },
    { key: 'errors', label: 'Errors', type: 'number' },
  ];

  const renderConfigValue = (value: unknown): React.ReactNode => {
    if (value === null || value === undefined) return <span className="text-text-tertiary">—</span>;
    if (typeof value === 'boolean') return <span className={value ? 'text-success' : 'text-text-tertiary'}>{String(value)}</span>;
    if (typeof value === 'number') return <span className="font-mono">{value}</span>;
    if (typeof value === 'string') return <span>{value}</span>;
    if (Array.isArray(value)) return <span>{value.join(', ') || '—'}</span>;
    if (typeof value === 'object') {
      return (
        <div className="ml-4 space-y-1">
          {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
            <div key={k} className="flex gap-2 text-sm">
              <span className="text-text-secondary">{k}:</span>
              {renderConfigValue(v)}
            </div>
          ))}
        </div>
      );
    }
    return <span>{String(value)}</span>;
  };

  return (
    <PageContainer>
      <div className="mb-6">
        <Link to="/strategies" className="text-sm text-text-secondary hover:text-text-primary transition-colors">
          &larr; Back to Strategies
        </Link>
      </div>

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-semibold text-text-primary">{strategy.name}</h1>
          <span className="text-sm text-text-secondary font-mono">v{strategy.currentVersion}</span>
          <StatusPill status={strategy.status} />
        </div>
        <div className="flex gap-2">
          {strategy.status === 'enabled' && (
            <button onClick={() => pauseMutation.mutate()} className="px-3 py-1.5 text-sm border border-border rounded hover:bg-surface-hover text-text-primary">Pause</button>
          )}
          {(strategy.status === 'paused' || strategy.status === 'draft') && (
            <button onClick={() => enableMutation.mutate()} className="px-3 py-1.5 text-sm border border-border rounded hover:bg-surface-hover text-text-primary">
              {strategy.status === 'draft' ? 'Enable' : 'Resume'}
            </button>
          )}
          <button onClick={() => navigate(`/strategies/${id}/edit`)} className="px-3 py-1.5 text-sm border border-border rounded hover:bg-surface-hover text-text-primary">Edit</button>
          {strategy.status !== 'disabled' && (
            <button onClick={() => disableMutation.mutate()} className="px-3 py-1.5 text-sm border border-error/30 rounded hover:bg-error/10 text-error">Disable</button>
          )}
        </div>
      </div>

      <TabContainer tabs={TABS}>
        {(activeTab) => (
          <>
            {activeTab === 'performance' && (
              <div className="space-y-6">
                <CardGrid>
                  <StatCard label="Total PnL" value={metrics ? formatPnl(metrics.totalPnl) : '—'} trend={metrics ? (metrics.totalPnl >= 0 ? 'up' : 'down') : undefined} />
                  <StatCard label="Win Rate" value={metrics ? formatPercent(metrics.winRate) : '—'} />
                  <StatCard label="Total Trades" value={metrics ? metrics.totalTrades.toLocaleString() : '—'} />
                  <StatCard label="Profit Factor" value={metrics ? metrics.profitFactor.toFixed(2) : '—'} />
                </CardGrid>

                <ChartContainer title="Strategy Equity Curve" loading={!equityData} empty={!equityData?.length}>
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={equityData ?? []}>
                      <defs>
                        <linearGradient id="strategyEquityGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={COLORS.success} stopOpacity={0.3} />
                          <stop offset="95%" stopColor={COLORS.success} stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="timestamp" tick={{ fill: COLORS.textTertiary, fontSize: 11 }} tickFormatter={(v) => new Date(v).toLocaleDateString()} />
                      <YAxis tick={{ fill: COLORS.textTertiary, fontSize: 11 }} tickFormatter={(v) => `$${v.toLocaleString()}`} />
                      <RechartsTooltip contentStyle={{ backgroundColor: COLORS.surface, border: `1px solid ${COLORS.border}`, borderRadius: 8 }} labelStyle={{ color: COLORS.textSecondary }} />
                      <Area type="monotone" dataKey="equity" stroke={COLORS.success} fill="url(#strategyEquityGrad)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </ChartContainer>

                {metrics && (
                  <div className="bg-surface rounded-lg border border-border p-4">
                    <h3 className="text-sm font-medium text-text-primary mb-4">Metrics</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {[
                        { label: 'Avg Winner', value: formatCurrency(metrics.avgWinner) },
                        { label: 'Avg Loser', value: formatCurrency(metrics.avgLoser) },
                        { label: 'Risk/Reward', value: metrics.riskReward.toFixed(2) },
                        { label: 'Max Drawdown', value: formatPercent(metrics.maxDrawdown) },
                        { label: 'Sharpe Ratio', value: metrics.sharpeRatio.toFixed(2) },
                        { label: 'Avg Hold Time', value: `${metrics.avgHoldBars} bars` },
                        { label: 'Dividend Income', value: formatCurrency(metrics.dividendIncome) },
                      ].map((m) => (
                        <div key={m.label}>
                          <p className="text-xs text-text-secondary">{m.label}</p>
                          <p className="text-sm font-mono text-text-primary">{m.value}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <DataTable
                  columns={tradeColumns}
                  data={(closedTrades ?? []) as TradeRecord[]}
                  emptyMessage="No closed trades yet"
                  keyField="id"
                />
              </div>
            )}

            {activeTab === 'positions' && (
              <div className="space-y-4">
                {positionsData.length === 0 ? (
                  <EmptyState message="No open positions for this strategy" />
                ) : (
                  <DataTable columns={positionColumns} data={positionsData} keyField="id" />
                )}

                {editPositionId && (
                  <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setEditPositionId(null)}>
                    <div className="bg-surface border border-border rounded-lg p-6 w-96 space-y-4" onClick={(e) => e.stopPropagation()}>
                      <h3 className="text-lg font-medium text-text-primary">Edit SL/TP</h3>
                      <div className="space-y-3">
                        <div>
                          <label className="text-sm text-text-secondary">Stop Loss</label>
                          <input type="number" value={slValue} onChange={(e) => setSlValue(e.target.value)} placeholder="Price level" className="w-full bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary font-mono mt-1" />
                        </div>
                        <div>
                          <label className="text-sm text-text-secondary">Take Profit</label>
                          <input type="number" value={tpValue} onChange={(e) => setTpValue(e.target.value)} placeholder="Price level" className="w-full bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary font-mono mt-1" />
                        </div>
                      </div>
                      <div className="flex justify-end gap-2">
                        <button onClick={() => setEditPositionId(null)} className="px-3 py-1.5 text-sm border border-border rounded hover:bg-surface-hover text-text-primary">Cancel</button>
                        <button
                          onClick={() => saveOverrideMutation.mutate({
                            posId: editPositionId,
                            sl: slValue ? parseFloat(slValue) : null,
                            tp: tpValue ? parseFloat(tpValue) : null,
                          })}
                          className="px-3 py-1.5 text-sm bg-accent text-white rounded hover:bg-accent/80"
                        >Save</button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'signals' && (
              <DataTable
                columns={signalColumns}
                data={(signals ?? []) as Record<string, unknown>[]}
                emptyMessage="No signals for this strategy"
                keyField="id"
              />
            )}

            {activeTab === 'config' && (
              <div className="space-y-6">
                <div className="bg-surface rounded-lg border border-border p-4">
                  <h3 className="text-sm font-medium text-text-primary mb-4">Current Config (v{strategy.currentVersion})</h3>
                  <div className="space-y-2">
                    {Object.entries(strategy.config).map(([key, value]) => (
                      <div key={key} className="flex gap-2 text-sm py-1 border-b border-border/50 last:border-0">
                        <span className="text-text-secondary font-medium min-w-[160px]">{key}</span>
                        <div className="text-text-primary">{renderConfigValue(value)}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-surface rounded-lg border border-border p-4">
                  <h3 className="text-sm font-medium text-text-primary mb-4">Version History</h3>
                  {(versions ?? []).length === 0 ? (
                    <p className="text-sm text-text-tertiary">No version history available</p>
                  ) : (
                    <div className="space-y-3">
                      {(versions ?? []).map((v) => (
                        <div key={v.version} className="flex items-start gap-3 text-sm border-b border-border/50 pb-3 last:border-0">
                          <span className="font-mono text-accent">v{v.version}</span>
                          <span className="text-text-secondary">{formatDateTime(v.createdAt)}</span>
                          {v.changes.length > 0 && (
                            <ul className="text-text-tertiary">
                              {v.changes.map((c, i) => <li key={i}>{c}</li>)}
                            </ul>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'evaluations' && (
              <div className="space-y-0">
                <DataTable
                  columns={evalColumns}
                  data={(evaluations ?? []) as EvalRecord[]}
                  emptyMessage="No evaluations recorded yet"
                  keyField="id"
                />
                {expandedEvalId && (() => {
                  const evalRow = (evaluations ?? []).find((e) => e.id === expandedEvalId);
                  if (!evalRow) return null;
                  return (
                    <div className="bg-surface border border-border rounded-b-lg p-4 -mt-1 text-sm space-y-2">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <div>
                          <span className="text-text-secondary">Strategy Version: </span>
                          <span className="font-mono text-text-primary">v{evalRow.strategyVersion}</span>
                        </div>
                        <div>
                          <span className="text-text-secondary">Duration: </span>
                          <span className="font-mono text-text-primary">{evalRow.durationMs}ms</span>
                        </div>
                        <div>
                          <span className="text-text-secondary">Symbols Evaluated: </span>
                          <span className="font-mono text-text-primary">{evalRow.symbolsEvaluated}</span>
                        </div>
                        <div>
                          <span className="text-text-secondary">Errors: </span>
                          <span className={`font-mono ${evalRow.errors > 0 ? 'text-error' : 'text-text-primary'}`}>{evalRow.errors}</span>
                        </div>
                      </div>
                      {evalRow.skipReason && (
                        <div>
                          <span className="text-text-secondary">Skip Reason: </span>
                          <span className="text-warning">{evalRow.skipReason}</span>
                        </div>
                      )}
                      <div className="flex gap-4">
                        <span className="text-text-secondary">Signals Emitted: <span className="font-mono text-text-primary">{evalRow.signalsEmitted}</span></span>
                        <span className="text-text-secondary">Exits Triggered: <span className="font-mono text-text-primary">{evalRow.exitsTriggered}</span></span>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}

            {activeTab === 'backtest' && (
              <BacktestForm
                strategyId={id!}
                onComplete={(backtestId) => navigate(`/backtests/${backtestId}`)}
              />
            )}

            {activeTab === 'backtestResults' && (
              <BacktestResultsList strategyId={id!} />
            )}
          </>
        )}
      </TabContainer>

      <ConfirmDialog
        open={closePositionId !== null}
        title="Close Position"
        message={
          selectedClosePos
            ? `Close ${selectedClosePos.qty} units of ${selectedClosePos.symbol}? This will create a manual exit signal.`
            : ''
        }
        confirmLabel="Close Position"
        variant="danger"
        onConfirm={() => {
          if (selectedClosePos) closePositionMutation.mutate(selectedClosePos as unknown as Position);
        }}
        onCancel={() => setClosePositionId(null)}
      />
    </PageContainer>
  );
}
