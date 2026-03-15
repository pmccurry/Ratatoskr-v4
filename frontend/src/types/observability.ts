export interface AuditEvent {
  id: string;
  eventType: string;
  category: string;
  severity: string;
  sourceModule: string;
  entityType: string | null;
  entityId: string | null;
  strategyId: string | null;
  symbol: string | null;
  summary: string;
  detailsJson: Record<string, unknown> | null;
  ts: string;
  createdAt: string;
}

export interface AlertInstance {
  id: string;
  ruleId: string;
  severity: string;
  summary: string;
  detailsJson: Record<string, unknown> | null;
  status: string;
  triggeredAt: string;
  acknowledgedAt: string | null;
  acknowledgedBy: string | null;
  resolvedAt: string | null;
  notificationsSent: string[] | null;
}

export interface AlertRule {
  id: string;
  name: string;
  description: string;
  category: string;
  conditionType: string;
  conditionConfig: Record<string, unknown>;
  severity: string;
  enabled: boolean;
  cooldownSeconds: number;
  notificationChannels: string[];
  createdAt: string;
}

export interface SystemHealth {
  overallStatus: string;
  uptimeSeconds: number;
  modules: Record<string, { status: string }>;
  pipeline: Record<string, string>;
}

export interface PipelineStatus {
  marketData: { status: string };
  strategies: { status: string };
  signals: { status: string };
  risk: { status: string };
  paperTrading: { status: string };
  portfolio: { status: string };
}
