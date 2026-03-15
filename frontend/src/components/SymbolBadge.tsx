export function SymbolBadge({ symbol, market }: { symbol: string; market?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-text-primary font-medium">
      {symbol}
      {market && (
        <span className="text-sm text-text-tertiary uppercase">{market}</span>
      )}
    </span>
  );
}
