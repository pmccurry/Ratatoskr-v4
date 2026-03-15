function toNumber(value: unknown): number | null {
  if (typeof value === 'number' && !isNaN(value)) return value;
  if (typeof value === 'string') {
    const parsed = parseFloat(value);
    if (!isNaN(parsed)) return parsed;
  }
  return null;
}

export function formatPrice(value: unknown, market?: string): string {
  const num = toNumber(value);
  if (num === null) return '—';
  if (market === 'forex') {
    return num.toFixed(5);
  }
  return `$${num.toFixed(2)}`;
}

export function formatPnl(value: unknown): string {
  const num = toNumber(value);
  if (num === null) return '—';
  const sign = num >= 0 ? '+' : '-';
  const formatted = Math.abs(num).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${sign}$${formatted}`;
}

export function formatPercent(value: unknown, decimals = 2): string {
  const num = toNumber(value);
  if (num === null) return '—';
  const sign = num >= 0 ? '+' : '-';
  return `${sign}${Math.abs(num).toFixed(decimals)}%`;
}

export function formatNumber(value: unknown): string {
  const num = toNumber(value);
  if (num === null) return '—';
  return num.toLocaleString('en-US');
}

export function formatCurrency(value: unknown): string {
  const num = toNumber(value);
  if (num === null) return '—';
  return `$${num.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function formatBasisPoints(value: unknown): string {
  const num = toNumber(value);
  if (num === null) return '—';
  return `${num}bps`;
}

export function formatDateTime(value: unknown): string {
  if (value == null || typeof value !== 'string') return '—';
  const date = new Date(value);
  if (isNaN(date.getTime())) return '—';
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

export function formatTimeAgo(value: unknown): string {
  if (value == null || typeof value !== 'string') return '—';
  const then = new Date(value).getTime();
  if (isNaN(then)) return '—';
  const now = Date.now();
  const diffMs = now - then;
  const diffSec = Math.floor(diffMs / 1000);

  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}h ago`;
  const diffDay = Math.floor(diffHour / 24);
  return `${diffDay}d ago`;
}

export function formatDecimal(value: string | number | null | undefined, decimals: number): string {
  const num = toNumber(value);
  if (num === null) return '—';
  return num.toFixed(decimals);
}
