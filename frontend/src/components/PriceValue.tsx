import { formatPrice } from '@/lib/formatters';

interface PriceValueProps {
  value: number;
  market?: string;
  className?: string;
}

export function PriceValue({ value, market, className = '' }: PriceValueProps) {
  return (
    <span className={`font-mono text-text-primary ${className}`}>
      {formatPrice(value, market)}
    </span>
  );
}
