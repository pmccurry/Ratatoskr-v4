export interface RiskDecision {
  id: string;
  signalId: string;
  status: string;
  checksPassed: string[];
  failedCheck: string | null;
  reasonCode: string | null;
  reasonText: string | null;
  modificationsJson: Record<string, unknown> | null;
  portfolioStateSnapshot: Record<string, unknown>;
  ts: string;
  createdAt: string;
}

export interface RiskOverview {
  killSwitch: {
    global: boolean;
    perStrategy: Record<string, boolean>;
  };
  drawdown: {
    current: number;
    limit: number;
    percent: number;
  };
  dailyLoss: {
    current: number;
    limit: number;
    percent: number;
  };
  totalExposure: {
    current: number;
    limit: number;
    percent: number;
  };
  symbolExposure: Record<string, number>;
  strategyExposure: Record<string, number>;
  recentDecisions: RiskDecision[];
}

export interface RiskConfig {
  maxPositionSizePercent: number;
  maxSymbolExposurePercent: number;
  maxStrategyExposurePercent: number;
  maxTotalExposurePercent: number;
  maxDrawdownPercent: number;
  maxDrawdownCatastrophicPercent: number;
  maxDailyLossPercent: number;
  minPositionValue: number;
  updatedAt: string;
}
