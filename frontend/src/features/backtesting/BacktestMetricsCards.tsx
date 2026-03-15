import { CardGrid, StatCard } from '@/components';
import { formatPnl, formatPercent } from '@/lib/formatters';

interface BacktestMetricsCardsProps {
  metrics: Record<string, number> | null;
  loading?: boolean;
}

export function BacktestMetricsCards({ metrics, loading }: BacktestMetricsCardsProps) {
  if (loading) {
    return (
      <CardGrid columns={3}>
        {Array.from({ length: 6 }).map((_, i) => (
          <StatCard key={i} label="" value="" loading />
        ))}
      </CardGrid>
    );
  }

  const val = (key: string): number | null =>
    metrics && metrics[key] != null ? metrics[key] : null;

  const wins = val('winning_trades');
  const losses = val('losing_trades');
  const winLossSubtitle =
    wins != null && losses != null ? `${wins}W / ${losses}L` : undefined;

  const profitFactor = val('profit_factor');
  const profitFactorDisplay =
    profitFactor == null || !isFinite(profitFactor) ? '\u221E' : profitFactor.toFixed(2);

  const netPnl = val('net_pnl');
  const maxDd = val('max_drawdown_pct');
  const sharpe = val('sharpe_ratio');
  const winRate = val('win_rate');
  const totalTrades = val('total_trades');

  return (
    <CardGrid columns={3}>
      <StatCard
        label="Net PnL"
        value={netPnl != null ? formatPnl(netPnl) : '\u2014'}
        trend={netPnl != null ? (netPnl >= 0 ? 'up' : 'down') : undefined}
      />
      <StatCard
        label="Win Rate"
        value={winRate != null ? formatPercent(winRate) : '\u2014'}
        subtitle={winLossSubtitle}
      />
      <StatCard
        label="Profit Factor"
        value={profitFactorDisplay}
      />
      <StatCard
        label="Sharpe Ratio"
        value={sharpe != null ? sharpe.toFixed(2) : '\u2014'}
      />
      <StatCard
        label="Max Drawdown"
        value={maxDd != null ? formatPercent(maxDd) : '\u2014'}
        trend={maxDd != null && maxDd > 0 ? 'down' : undefined}
      />
      <StatCard
        label="Total Trades"
        value={totalTrades != null ? totalTrades : '\u2014'}
      />
    </CardGrid>
  );
}
