import api from '@/lib/api';

export interface BacktestParams {
  symbols: string[];
  timeframe: string;
  startDate: string;
  endDate: string;
  initialCapital: number;
  positionSizing: { type: string; amount?: number; percent?: number; stopPips?: number };
  exitConfig: {
    stopLossPips?: number;
    takeProfitPips?: number;
    signalExit?: boolean;
    maxHoldBars?: number;
  };
}

export interface BacktestRun {
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
  createdAt: string;
}

export interface BacktestTrade {
  id: string;
  backtestId: string;
  symbol: string;
  side: string;
  quantity: number;
  entryTime: string;
  entryPrice: number;
  entryBarIndex: number;
  exitTime: string | null;
  exitPrice: number | null;
  exitBarIndex: number | null;
  exitReason: string | null;
  pnl: number | null;
  pnlPercent: number | null;
  fees: number | null;
  holdBars: number | null;
  maxFavorable: number | null;
  maxAdverse: number | null;
}

export interface EquityPoint {
  barTime: string;
  barIndex: number;
  equity: number;
  cash: number;
  openPositions: number;
  unrealizedPnl: number;
  drawdownPct: number;
}

export const runBacktest = (strategyId: string, params: BacktestParams) =>
  api.post(`/strategies/${strategyId}/backtest`, params, { timeout: 300000 });

export const getBacktest = (backtestId: string) =>
  api.get(`/backtesting/${backtestId}`);

export const getBacktestTrades = (backtestId: string, page = 1, pageSize = 50) =>
  api.get(`/backtesting/${backtestId}/trades`, { params: { page, pageSize } });

export const getBacktestEquityCurve = (backtestId: string, sample = 200) =>
  api.get(`/backtesting/${backtestId}/equity-curve`, { params: { sample } });

export const getStrategyBacktests = (strategyId: string, page = 1, pageSize = 20) =>
  api.get(`/strategies/${strategyId}/backtests`, { params: { page, pageSize } });
