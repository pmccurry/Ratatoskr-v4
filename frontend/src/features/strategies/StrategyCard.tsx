import { StatusPill, PnlValue, TimeAgo } from '@/components';
import { formatPercent } from '@/lib/formatters';
import type { Strategy } from '@/types/strategy';

interface StrategyCardProps {
  strategy: Strategy;
  onPause?: () => void;
  onResume?: () => void;
  onEdit?: () => void;
  onDetail?: () => void;
}

function getStatusDotColor(strategy: Strategy): string {
  if (strategy.autoPauseErrorCount > 0) return 'bg-error';
  switch (strategy.status) {
    case 'enabled':
      return 'bg-success';
    case 'paused':
      return 'bg-warning';
    case 'disabled':
    case 'draft':
    default:
      return 'bg-text-tertiary';
  }
}

export function StrategyCard({
  strategy,
  onPause,
  onResume,
  onEdit,
  onDetail,
}: StrategyCardProps) {
  const s = strategy as unknown as Record<string, unknown>;
  const totalPnl = typeof s.totalPnl === 'number' ? s.totalPnl : undefined;
  const winRate = typeof s.winRate === 'number' ? s.winRate : undefined;
  const openPositions = typeof s.openPositions === 'number' ? s.openPositions : undefined;
  const signalsToday = typeof s.signalsToday === 'number' ? s.signalsToday : undefined;
  const symbolCount = typeof s.symbolCount === 'number' ? s.symbolCount : undefined;
  const timeframe = typeof s.timeframe === 'string' ? s.timeframe : undefined;

  const isAutoPaused = strategy.autoPauseErrorCount > 0;
  const isDraft = strategy.status === 'draft';
  const isPaused = strategy.status === 'paused';

  const handleCardClick = () => {
    onDetail?.();
  };

  const stopAndCall = (fn?: () => void) => (e: React.MouseEvent) => {
    e.stopPropagation();
    fn?.();
  };

  return (
    <div
      className="bg-surface rounded-lg border border-border p-4 hover:border-border-strong transition-colors cursor-pointer"
      onClick={handleCardClick}
    >
      {/* Header row: status dot, name, version, status pill */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className={`w-2 h-2 rounded-full inline-block flex-shrink-0 ${getStatusDotColor(strategy)}`}
          />
          <span className="text-text-primary font-medium truncate">
            {strategy.name}
          </span>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-text-secondary text-xs">v{strategy.currentVersion}</span>
          <StatusPill status={strategy.status} />
        </div>
      </div>

      {/* Meta row: market, timeframe, symbol count */}
      <div className="text-text-secondary text-xs mt-1">
        {strategy.market}
        {timeframe && <> &middot; {timeframe}</>}
        {symbolCount !== undefined && <> &middot; {symbolCount} symbol{symbolCount !== 1 ? 's' : ''}</>}
      </div>

      {/* Auto-pause warning */}
      {isAutoPaused && (
        <div className="bg-warning/10 text-warning text-xs px-2 py-1 rounded mt-2">
          Auto-paused: {strategy.autoPauseErrorCount} error{strategy.autoPauseErrorCount !== 1 ? 's' : ''}
        </div>
      )}

      {/* Stats row */}
      <div className="flex items-center gap-4 mt-3 text-xs">
        {totalPnl !== undefined && (
          <span>
            PnL: <PnlValue value={totalPnl} />
          </span>
        )}
        {winRate !== undefined && (
          <span className="text-text-secondary">
            Win: {formatPercent(winRate, 0)}
          </span>
        )}
        {openPositions !== undefined && (
          <span className="text-text-secondary">
            Pos: {openPositions}
          </span>
        )}
      </div>

      {/* Eval / signals row */}
      <div className="flex items-center gap-4 mt-1 text-xs">
        {strategy.lastEvaluatedAt && (
          <span className="text-text-secondary">
            Last eval: <TimeAgo value={strategy.lastEvaluatedAt} />
          </span>
        )}
        {signalsToday !== undefined && (
          <span className="text-text-secondary">
            Signals today: {signalsToday}
          </span>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border">
        {isDraft ? (
          <button
            className="px-3 py-1.5 text-xs border border-border rounded hover:bg-surface-hover text-text-primary"
            onClick={stopAndCall(onResume)}
          >
            Enable
          </button>
        ) : isPaused || isAutoPaused ? (
          <button
            className="px-3 py-1.5 text-xs border border-border rounded hover:bg-surface-hover text-text-primary"
            onClick={stopAndCall(onResume)}
          >
            Resume
          </button>
        ) : strategy.status === 'enabled' ? (
          <button
            className="px-3 py-1.5 text-xs border border-border rounded hover:bg-surface-hover text-text-primary"
            onClick={stopAndCall(onPause)}
          >
            Pause
          </button>
        ) : null}
        <button
          className="px-3 py-1.5 text-xs border border-border rounded hover:bg-surface-hover text-text-primary"
          onClick={stopAndCall(onEdit)}
        >
          Edit
        </button>
        <button
          className="px-3 py-1.5 text-xs border border-border rounded hover:bg-surface-hover text-text-primary ml-auto"
          onClick={stopAndCall(onDetail)}
        >
          Detail &rarr;
        </button>
      </div>
    </div>
  );
}
