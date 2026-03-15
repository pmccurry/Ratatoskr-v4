import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import api from '@/lib/api';
import { formatDateTime } from '@/lib/formatters';
import { PageContainer, StatusPill, LoadingState, ErrorState } from '@/components';
import { BacktestMetricsCards } from './BacktestMetricsCards';
import { EquityCurveChart } from './EquityCurveChart';
import { BacktestTradeTable } from './BacktestTradeTable';
import type { EquityPoint } from './EquityCurveChart';

interface BacktestRun {
  id: string;
  strategyId: string;
  status: string;
  symbols: string[];
  timeframe: string;
  startDate: string;
  endDate: string;
  initialCapital: number;
  positionSizing: Record<string, unknown>;
  exitConfig: Record<string, unknown>;
  startedAt: string | null;
  completedAt: string | null;
  durationSeconds: number | null;
  metrics: Record<string, number> | null;
  barsProcessed: number | null;
  totalTrades: number | null;
  error: string | null;
  createdAt: string | null;
}

async function getBacktest(id: string): Promise<BacktestRun> {
  const res = await api.get(`/backtesting/${id}`);
  return res.data;
}

async function getBacktestEquityCurve(id: string, sample: number): Promise<EquityPoint[]> {
  const res = await api.get(`/backtesting/${id}/equity-curve`, { params: { sample } });
  return res.data;
}

function formatDuration(seconds: number | null): string {
  if (seconds == null) return '\u2014';
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}


export function BacktestDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const {
    data: run,
    isLoading: runLoading,
    error: runError,
  } = useQuery<BacktestRun>({
    queryKey: ['backtest', id],
    queryFn: () => getBacktest(id!),
    enabled: !!id,
  });

  const {
    data: equityData,
    isLoading: equityLoading,
  } = useQuery<EquityPoint[]>({
    queryKey: ['backtest', id, 'equity-curve'],
    queryFn: () => getBacktestEquityCurve(id!, 300),
    enabled: !!id && run?.status === 'completed',
  });

  if (runLoading) return <PageContainer><LoadingState /></PageContainer>;
  if (runError || !run) return <PageContainer><ErrorState message="Failed to load backtest" /></PageContainer>;

  const dateRange = `${formatDateTime(run.startDate)} \u2014 ${formatDateTime(run.endDate)}`;

  return (
    <PageContainer>
      {/* Back link */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary mb-4 transition-colors"
      >
        <ArrowLeft size={16} />
        Back
      </button>

      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-xl font-semibold text-text-primary">Backtest Results</h1>
          <StatusPill status={run.status} />
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-text-secondary">
          <span>Symbols: {run.symbols.join(', ')}</span>
          <span>Timeframe: {run.timeframe}</span>
          <span>Period: {dateRange}</span>
          <span>Duration: {formatDuration(run.durationSeconds)}</span>
          {run.barsProcessed != null && <span>Bars: {run.barsProcessed.toLocaleString()}</span>}
        </div>
        {run.error && (
          <div className="mt-3 p-3 rounded bg-error/10 border border-error/30 text-sm text-error">
            {run.error}
          </div>
        )}
      </div>

      {/* Metrics */}
      <div className="mb-6">
        <BacktestMetricsCards
          metrics={run.metrics}
          loading={runLoading}
        />
      </div>

      {/* Equity Curve */}
      <div className="mb-6">
        <EquityCurveChart
          data={equityData ?? []}
          initialCapital={run.initialCapital}
          loading={equityLoading}
        />
      </div>

      {/* Trade Table */}
      <BacktestTradeTable backtestId={id!} />
    </PageContainer>
  );
}
