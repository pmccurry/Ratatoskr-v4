import { formatPnl } from '@/lib/formatters';

interface PnlValueProps {
  value: number;
  className?: string;
}

export function PnlValue({ value, className = '' }: PnlValueProps) {
  const color = value >= 0 ? 'text-success' : 'text-error';
  return (
    <span className={`font-mono ${color} ${className}`}>
      {formatPnl(value)}
    </span>
  );
}
