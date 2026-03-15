import { useEffect, useState } from 'react';
import { formatTimeAgo } from '@/lib/formatters';

export function TimeAgo({ value, className = '' }: { value: string; className?: string }) {
  const [display, setDisplay] = useState(formatTimeAgo(value));

  useEffect(() => {
    const interval = setInterval(() => {
      setDisplay(formatTimeAgo(value));
    }, 10_000);
    return () => clearInterval(interval);
  }, [value]);

  return <span className={`text-text-secondary ${className}`}>{display}</span>;
}
