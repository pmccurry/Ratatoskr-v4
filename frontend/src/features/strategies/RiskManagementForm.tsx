const STOP_LOSS_TYPES = [
  { value: 'percent', label: 'Percent' },
  { value: 'atr_multiple', label: 'ATR Multiple' },
  { value: 'fixed', label: 'Fixed' },
];

const TAKE_PROFIT_TYPES = [
  { value: 'percent', label: 'Percent' },
  { value: 'atr_multiple', label: 'ATR Multiple' },
  { value: 'fixed', label: 'Fixed' },
  { value: 'risk_multiple', label: 'Risk Multiple' },
];

const TRAILING_STOP_TYPES = [
  { value: 'percent', label: 'Percent' },
  { value: 'atr_multiple', label: 'ATR Multiple' },
];

interface RiskManagementValue {
  stopLoss: { type: string; value: number };
  takeProfit: { type: string; value: number };
  trailingStop: { enabled: boolean; type: string; value: number };
  maxHoldBars: number | null;
}

interface RiskManagementFormProps {
  value: RiskManagementValue;
  onChange: (value: RiskManagementValue) => void;
}

const selectClass =
  'bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary w-full focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent';

const numberClass =
  'bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary font-mono w-full focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent';

export function RiskManagementForm({
  value,
  onChange,
}: RiskManagementFormProps) {
  return (
    <div className="space-y-4">
      {/* Stop Loss */}
      <div className="grid grid-cols-3 gap-4 items-center">
        <label className="text-sm text-text-secondary">Stop Loss</label>
        <select
          value={value.stopLoss.type}
          onChange={(e) =>
            onChange({
              ...value,
              stopLoss: { ...value.stopLoss, type: e.target.value },
            })
          }
          className={selectClass}
        >
          {STOP_LOSS_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        <input
          type="number"
          min={0}
          step="any"
          value={value.stopLoss.value}
          onChange={(e) =>
            onChange({
              ...value,
              stopLoss: {
                ...value.stopLoss,
                value: parseFloat(e.target.value) || 0,
              },
            })
          }
          className={numberClass}
        />
      </div>

      {/* Take Profit */}
      <div className="grid grid-cols-3 gap-4 items-center">
        <label className="text-sm text-text-secondary">Take Profit</label>
        <select
          value={value.takeProfit.type}
          onChange={(e) =>
            onChange({
              ...value,
              takeProfit: { ...value.takeProfit, type: e.target.value },
            })
          }
          className={selectClass}
        >
          {TAKE_PROFIT_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        <input
          type="number"
          min={0}
          step="any"
          value={value.takeProfit.value}
          onChange={(e) =>
            onChange({
              ...value,
              takeProfit: {
                ...value.takeProfit,
                value: parseFloat(e.target.value) || 0,
              },
            })
          }
          className={numberClass}
        />
      </div>

      {/* Trailing Stop */}
      <div className="space-y-2">
        <div className="grid grid-cols-3 gap-4 items-center">
          <label className="text-sm text-text-secondary">Trailing Stop</label>
          <div className="col-span-2 flex items-center gap-2">
            <button
              type="button"
              role="switch"
              aria-checked={value.trailingStop.enabled}
              onClick={() =>
                onChange({
                  ...value,
                  trailingStop: {
                    ...value.trailingStop,
                    enabled: !value.trailingStop.enabled,
                  },
                })
              }
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border border-border transition-colors ${
                value.trailingStop.enabled ? 'bg-accent' : 'bg-surface'
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-text-primary shadow transition-transform ${
                  value.trailingStop.enabled ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
            <span className="text-sm text-text-secondary">
              {value.trailingStop.enabled ? 'Enabled' : 'Disabled'}
            </span>
          </div>
        </div>

        {value.trailingStop.enabled && (
          <div className="grid grid-cols-3 gap-4 items-center">
            <span />
            <select
              value={value.trailingStop.type}
              onChange={(e) =>
                onChange({
                  ...value,
                  trailingStop: {
                    ...value.trailingStop,
                    type: e.target.value,
                  },
                })
              }
              className={selectClass}
            >
              {TRAILING_STOP_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            <input
              type="number"
              min={0}
              step="any"
              value={value.trailingStop.value}
              onChange={(e) =>
                onChange({
                  ...value,
                  trailingStop: {
                    ...value.trailingStop,
                    value: parseFloat(e.target.value) || 0,
                  },
                })
              }
              className={numberClass}
            />
          </div>
        )}
      </div>

      {/* Max Hold Bars */}
      <div className="grid grid-cols-3 gap-4 items-center">
        <label className="text-sm text-text-secondary">Max Hold Bars</label>
        <div className="col-span-2 flex items-center gap-3">
          <input
            type="number"
            min={1}
            step={1}
            value={value.maxHoldBars ?? ''}
            placeholder="No limit"
            onChange={(e) => {
              const raw = e.target.value;
              onChange({
                ...value,
                maxHoldBars: raw === '' ? null : parseInt(raw, 10) || null,
              });
            }}
            className={numberClass}
          />
        </div>
      </div>
    </div>
  );
}
