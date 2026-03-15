export interface PortfolioSummary {
  equity: number;
  cash: number;
  positionsValue: number;
  unrealizedPnl: number;
  realizedPnlTotal: number;
  totalReturn: number;
  totalReturnPercent: number;
  drawdownPercent: number;
  peakEquity: number;
  openPositionsCount: number;
}

export interface EquityBreakdown {
  totalEquity: number;
  totalCash: number;
  totalPositionsValue: number;
  equitiesCash: number;
  equitiesPositionsValue: number;
  forexCash: number;
  forexPositionsValue: number;
}

export interface CashBalance {
  accountScope: string;
  balance: number;
}

export interface PortfolioSnapshot {
  id: string;
  ts: string;
  cashBalance: number;
  positionsValue: number;
  equity: number;
  unrealizedPnl: number;
  realizedPnlToday: number;
  realizedPnlTotal: number;
  drawdownPercent: number;
  peakEquity: number;
  openPositionsCount: number;
  snapshotType: string;
  createdAt: string;
}

export interface RealizedPnlEntry {
  id: string;
  positionId: string;
  strategyId: string;
  symbol: string;
  market: string;
  side: string;
  qtyClosed: number;
  entryPrice: number;
  exitPrice: number;
  grossPnl: number;
  fees: number;
  netPnl: number;
  pnlPercent: number;
  holdingPeriodBars: number;
  closedAt: string;
}

export interface DividendPayment {
  id: string;
  positionId: string;
  symbol: string;
  exDate: string;
  payableDate: string;
  sharesHeld: number;
  amountPerShare: number;
  grossAmount: number;
  netAmount: number;
  status: string;
  paidAt: string | null;
}

export interface PerformanceMetrics {
  totalReturn: number;
  totalReturnPercent: number;
  totalPnl: number;
  winRate: number;
  profitFactor: number | null;
  averageWinner: number;
  averageLoser: number;
  riskRewardRatio: number | null;
  maxDrawdown: number;
  sharpeRatio: number | null;
  sortinoRatio: number | null;
  averageHoldBars: number;
  longestWinStreak: number;
  longestLossStreak: number;
  totalTrades: number;
  totalFees: number;
  totalDividendIncome: number;
}
