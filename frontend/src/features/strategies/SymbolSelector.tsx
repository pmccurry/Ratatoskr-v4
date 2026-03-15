import { useState, useRef, useMemo, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

interface WatchlistItem {
  symbol: string;
  market: string;
}

interface SymbolSelectorProps {
  selected: string[];
  onChange: (symbols: string[]) => void;
  market?: string;
}

export function SymbolSelector({
  selected,
  onChange,
  market,
}: SymbolSelectorProps) {
  const [search, setSearch] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: watchlist } = useQuery<WatchlistItem[]>({
    queryKey: ['market-data', 'watchlist'],
    queryFn: () => api.get('/market-data/watchlist').then((r) => r.data),
    staleTime: 300_000,
  });

  const filtered = useMemo(() => {
    if (!watchlist) return [];

    let items = watchlist;

    if (market) {
      items = items.filter((item) => item.market === market);
    }

    const query = search.trim().toLowerCase();
    if (query) {
      items = items.filter((item) =>
        item.symbol.toLowerCase().includes(query),
      );
    }

    return items.filter((item) => !selected.includes(item.symbol));
  }, [watchlist, market, search, selected]);

  const handleAdd = useCallback(
    (symbol: string) => {
      if (!selected.includes(symbol)) {
        onChange([...selected, symbol]);
      }
      setSearch('');
      inputRef.current?.focus();
    },
    [selected, onChange],
  );

  const handleRemove = useCallback(
    (symbol: string) => {
      onChange(selected.filter((s) => s !== symbol));
    },
    [selected, onChange],
  );

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={containerRef} className="relative w-full">
      {/* Selected chips */}
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {selected.map((symbol) => (
            <span
              key={symbol}
              className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-accent/20 text-accent rounded-full"
            >
              {symbol}
              <button
                type="button"
                onClick={() => handleRemove(symbol)}
                className="hover:text-error cursor-pointer"
                aria-label={`Remove ${symbol}`}
              >
                &times;
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Search input */}
      <input
        ref={inputRef}
        type="text"
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setIsOpen(true);
        }}
        onFocus={() => setIsOpen(true)}
        placeholder="Search symbols..."
        className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary w-full focus:outline-none focus:ring-1 focus:ring-accent"
      />

      {/* Dropdown */}
      {isOpen && filtered.length > 0 && (
        <ul className="absolute z-10 bg-surface border border-border rounded-lg shadow-lg mt-1 max-h-48 overflow-y-auto w-full">
          {filtered.map((item) => (
            <li
              key={item.symbol}
              onClick={() => handleAdd(item.symbol)}
              className="px-3 py-2 text-sm text-text-primary hover:bg-surface-hover cursor-pointer"
            >
              {item.symbol}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
