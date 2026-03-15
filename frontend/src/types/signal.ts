export interface Signal {
  id: string;
  strategyId: string;
  strategyVersion: number;
  symbol: string;
  market: string;
  timeframe: string;
  side: string;
  signalType: string;
  source: string;
  confidence: number;
  status: string;
  payloadJson: Record<string, unknown> | null;
  positionId: string | null;
  exitReason: string | null;
  ts: string;
  expiresAt: string;
  createdAt: string;
}

export interface SignalStats {
  total: number;
  byStatus: Record<string, number>;
  byStrategy: Record<string, number>;
  bySymbol: Record<string, number>;
  bySignalType: Record<string, number>;
  bySource: Record<string, number>;
}
