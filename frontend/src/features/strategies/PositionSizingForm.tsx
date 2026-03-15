const SIZING_METHODS = [
  { value: 'fixed_qty', label: 'Fixed Quantity' },
  { value: 'fixed_dollar', label: 'Fixed Dollar' },
  { value: 'percent_equity', label: '% of Equity' },
  { value: 'risk_based', label: 'Risk-Based' },
];

const VALUE_LABELS: Record<string, string> = {
  fixed_qty: 'Quantity',
  fixed_dollar: 'Dollar Amount',
  percent_equity: '% of Equity',
  risk_based: 'Risk %',
};

const ORDER_TYPES = [
  { value: 'market', label: 'Market' },
  { value: 'limit', label: 'Limit' },
];

interface PositionSizingValue {
  method: string;
  value: number;
  maxPositions: number;
  orderType: string;
}

interface PositionSizingFormProps {
  value: PositionSizingValue;
  onChange: (value: PositionSizingValue) => void;
}

const selectClass =
  'bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary w-full focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent';

const numberClass =
  'bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary font-mono w-full focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent';

export function PositionSizingForm({
  value,
  onChange,
}: PositionSizingFormProps) {
  return (
    <div className="space-y-4">
      {/* Method */}
      <div className="grid grid-cols-3 gap-4 items-center">
        <label className="text-sm text-text-secondary">Method</label>
        <div className="col-span-2">
          <select
            value={value.method}
            onChange={(e) => onChange({ ...value, method: e.target.value })}
            className={selectClass}
          >
            {SIZING_METHODS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Value */}
      <div className="grid grid-cols-3 gap-4 items-center">
        <label className="text-sm text-text-secondary">
          {VALUE_LABELS[value.method] ?? 'Value'}
        </label>
        <div className="col-span-2">
          <input
            type="number"
            min={0}
            step="any"
            value={value.value}
            onChange={(e) =>
              onChange({ ...value, value: parseFloat(e.target.value) || 0 })
            }
            className={numberClass}
          />
        </div>
      </div>

      {/* Max Positions */}
      <div className="grid grid-cols-3 gap-4 items-center">
        <label className="text-sm text-text-secondary">Max Positions</label>
        <div className="col-span-2">
          <input
            type="number"
            min={1}
            step={1}
            value={value.maxPositions}
            onChange={(e) =>
              onChange({
                ...value,
                maxPositions: Math.max(1, parseInt(e.target.value, 10) || 1),
              })
            }
            className={numberClass}
          />
        </div>
      </div>

      {/* Order Type */}
      <div className="grid grid-cols-3 gap-4 items-center">
        <label className="text-sm text-text-secondary">Order Type</label>
        <div className="col-span-2">
          <select
            value={value.orderType}
            onChange={(e) => onChange({ ...value, orderType: e.target.value })}
            className={selectClass}
          >
            {ORDER_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
