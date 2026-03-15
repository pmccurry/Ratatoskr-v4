export interface Strategy {
  id: string;
  key: string;
  name: string;
  description: string;
  type: string;
  status: string;
  currentVersion: number;
  market: string;
  autoPauseErrorCount: number;
  lastEvaluatedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface StrategyDetail extends Strategy {
  config: StrategyConfig;
}

export interface StrategyConfig {
  entryConditions: ConditionGroup;
  exitConditions: ConditionGroup;
  symbols: string[];
  timeframe: string;
  positionSizing: Record<string, unknown>;
  riskManagement: Record<string, unknown>;
  schedule: Record<string, unknown>;
}

export interface StrategyEvaluation {
  id: string;
  strategyId: string;
  strategyVersion: number;
  evaluatedAt: string;
  symbolsEvaluated: number;
  signalsEmitted: number;
  exitsTriggered: number;
  errors: number;
  durationMs: number;
  status: string;
  skipReason: string | null;
  createdAt: string;
}

export interface IndicatorDefinition {
  key: string;
  name: string;
  category: string;
  params: IndicatorParam[];
  outputs: string[];
  description: string;
}

export interface IndicatorParam {
  name: string;
  type: string;
  default: unknown;
  min?: number;
  max?: number;
  options?: string[];
}

export interface Condition {
  left: Operand;
  operator: string;
  right: Operand;
}

export interface ConditionGroup {
  logic: 'and' | 'or';
  conditions: (Condition | ConditionGroup)[];
}

export interface Operand {
  type: 'indicator' | 'formula' | 'value' | 'range';
  indicator?: string;
  params?: Record<string, unknown>;
  output?: string;
  expression?: string;
  value?: number;
  min?: number;
  max?: number;
}
