export interface Position {
  id: string;
  strategyId: string;
  symbol: string;
  market: string;
  side: string;
  qty: number;
  avgEntryPrice: number;
  costBasis: number;
  currentPrice: number;
  marketValue: number;
  unrealizedPnl: number;
  unrealizedPnlPercent: number;
  realizedPnl: number;
  totalFees: number;
  totalDividendsReceived: number;
  totalReturn: number;
  totalReturnPercent: number;
  status: string;
  openedAt: string;
  closedAt: string | null;
  closeReason: string | null;
  barsHeld: number;
  contractMultiplier: number;
  createdAt: string;
}
