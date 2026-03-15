export const COLORS = {
  background: '#0f1117',
  surface: '#1a1d27',
  surfaceHover: '#22252f',
  border: '#2a2d3a',
  borderStrong: '#3a3d4a',
  textPrimary: '#e4e4e7',
  textSecondary: '#a1a1aa',
  textTertiary: '#71717a',
  accent: '#3b82f6',
  accentHover: '#2563eb',
  success: '#22c55e',
  warning: '#eab308',
  error: '#ef4444',
  info: '#6366f1',
} as const;

export const REFRESH = {
  activityFeed: 10_000,
  signals: 10_000,
  positions: 30_000,
  riskOverview: 30_000,
  portfolioSummary: 60_000,
  strategyList: 60_000,
  equityCurve: 300_000,
  systemHealth: 10_000,
  statusBar: 30_000,
  alertBanner: 30_000,
} as const;

export const STALE = {
  indicatorCatalog: 3_600_000,
  strategyList: 30_000,
  signalList: 5_000,
  positionList: 15_000,
  portfolioSummary: 30_000,
  riskOverview: 15_000,
  systemHealth: 5_000,
} as const;

export const SIDEBAR_WIDTH = {
  expanded: 240,
  collapsed: 64,
} as const;
