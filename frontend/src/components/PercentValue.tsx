import { formatPercent } from '@/lib/formatters';

interface PercentValueProps {
  value: number;
  decimals?: number;
  colored?: boolean;
  className?: string;
}

export function PercentValue({ value, decimals = 2, colored = false, className = '' }: PercentValueProps) {
  const color = colored ? (value >= 0 ? 'text-success' : 'text-error') : 'text-text-primary';
  return (
    <span className={`font-mono ${color} ${className}`}>
      {formatPercent(value, decimals)}
    </span>
  );
}
