import { useId } from 'react';
import type { Condition, Operand, IndicatorDefinition } from '@/types/strategy';
import { OperatorSelect } from './OperatorSelect';

interface ConditionRowProps {
  condition: Condition;
  onChange: (condition: Condition) => void;
  onRemove: () => void;
  indicators: IndicatorDefinition[];
}

function groupIndicatorsByCategory(indicators: IndicatorDefinition[]) {
  const groups: Record<string, IndicatorDefinition[]> = {};
  for (const ind of indicators) {
    if (!groups[ind.category]) {
      groups[ind.category] = [];
    }
    groups[ind.category].push(ind);
  }
  return groups;
}

function isRangeOperator(operator: string): boolean {
  return operator === 'between' || operator === 'outside';
}

function getIndicatorDef(
  indicators: IndicatorDefinition[],
  key: string
): IndicatorDefinition | undefined {
  return indicators.find((ind) => ind.key === key);
}

const inputClass =
  'bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary';

export function ConditionRow({
  condition,
  onChange,
  onRemove,
  indicators,
}: ConditionRowProps) {
  const radioId = useId();
  const grouped = groupIndicatorsByCategory(indicators);
  const leftDef = condition.left.indicator
    ? getIndicatorDef(indicators, condition.left.indicator)
    : undefined;
  const isFormula = condition.left.type === 'formula';

  function updateLeft(patch: Partial<Operand>) {
    onChange({ ...condition, left: { ...condition.left, ...patch } });
  }

  function updateRight(patch: Partial<Operand>) {
    onChange({ ...condition, right: { ...condition.right, ...patch } });
  }

  function handleLeftIndicatorChange(key: string) {
    if (key === '__formula__') {
      updateLeft({
        type: 'formula',
        indicator: undefined,
        params: undefined,
        output: undefined,
        expression: '',
      });
      return;
    }

    const def = getIndicatorDef(indicators, key);
    const defaultParams: Record<string, unknown> = {};
    if (def) {
      for (const p of def.params) {
        defaultParams[p.name] = p.default;
      }
    }

    updateLeft({
      type: 'indicator',
      indicator: key,
      params: defaultParams,
      output: def && def.outputs.length > 1 ? def.outputs[0] : undefined,
      expression: undefined,
    });
  }

  function handleOperatorChange(operator: string) {
    const newCondition = { ...condition, operator };

    // When switching to/from range operators, adjust the right operand
    if (isRangeOperator(operator) && condition.right.type !== 'range') {
      newCondition.right = { type: 'range', min: 0, max: 100 };
    } else if (!isRangeOperator(operator) && condition.right.type === 'range') {
      newCondition.right = { type: 'value', value: 0 };
    }

    onChange(newCondition);
  }

  function renderIndicatorSelect(
    operand: Operand,
    onIndicatorChange: (key: string) => void,
    showFormula: boolean
  ) {
    const selectedValue =
      operand.type === 'formula' ? '__formula__' : operand.indicator || '';

    return (
      <select
        value={selectedValue}
        onChange={(e) => onIndicatorChange(e.target.value)}
        className={inputClass}
      >
        <option value="" disabled>
          Select indicator...
        </option>
        {Object.entries(grouped).map(([category, inds]) => (
          <optgroup key={category} label={category}>
            {inds.map((ind) => (
              <option key={ind.key} value={ind.key}>
                {ind.name}
              </option>
            ))}
          </optgroup>
        ))}
        {showFormula && (
          <optgroup label="Custom">
            <option value="__formula__">Custom Formula</option>
          </optgroup>
        )}
      </select>
    );
  }

  function renderLeftParams() {
    if (isFormula) {
      return (
        <input
          type="text"
          value={condition.left.expression || ''}
          onChange={(e) => updateLeft({ expression: e.target.value })}
          placeholder="e.g. (close - ema(close, 200)) / atr(14)"
          className={`${inputClass} min-w-[240px] font-mono`}
        />
      );
    }

    if (!leftDef) return null;

    return (
      <div className="flex items-center gap-2 flex-wrap">
        {/* Multi-output selector */}
        {leftDef.outputs.length > 1 && (
          <select
            value={condition.left.output || leftDef.outputs[0]}
            onChange={(e) => updateLeft({ output: e.target.value })}
            className={inputClass}
          >
            {leftDef.outputs.map((out) => (
              <option key={out} value={out}>
                {out}
              </option>
            ))}
          </select>
        )}

        {/* Dynamic parameters */}
        {leftDef.params.map((param) => {
          const currentValue =
            condition.left.params?.[param.name] ?? param.default;

          if (param.type === 'select' && param.options) {
            return (
              <label key={param.name} className="flex items-center gap-1">
                <span className="text-sm text-text-secondary">{param.name}:</span>
                <select
                  value={String(currentValue)}
                  onChange={(e) =>
                    updateLeft({
                      params: {
                        ...condition.left.params,
                        [param.name]: e.target.value,
                      },
                    })
                  }
                  className={inputClass}
                >
                  {param.options.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </label>
            );
          }

          // int or float
          const step = param.type === 'float' ? 0.1 : 1;
          return (
            <label key={param.name} className="flex items-center gap-1">
              <span className="text-sm text-text-secondary">{param.name}:</span>
              <input
                type="number"
                value={currentValue as number}
                step={step}
                min={param.min}
                max={param.max}
                onChange={(e) =>
                  updateLeft({
                    params: {
                      ...condition.left.params,
                      [param.name]:
                        param.type === 'int'
                          ? parseInt(e.target.value, 10)
                          : parseFloat(e.target.value),
                    },
                  })
                }
                className={`${inputClass} w-20`}
              />
            </label>
          );
        })}
      </div>
    );
  }

  function renderRightSide() {
    if (isRangeOperator(condition.operator)) {
      return (
        <div className="flex items-center gap-2">
          <input
            type="number"
            value={condition.right.min ?? 0}
            onChange={(e) =>
              updateRight({ min: parseFloat(e.target.value) })
            }
            placeholder="Min"
            className={`${inputClass} w-24`}
          />
          <span className="text-sm text-text-secondary">to</span>
          <input
            type="number"
            value={condition.right.max ?? 100}
            onChange={(e) =>
              updateRight({ max: parseFloat(e.target.value) })
            }
            placeholder="Max"
            className={`${inputClass} w-24`}
          />
        </div>
      );
    }

    const rightMode = condition.right.type === 'indicator' ? 'indicator' : 'value';

    return (
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1">
          <label className="flex items-center gap-1 text-sm text-text-secondary cursor-pointer">
            <input
              type="radio"
              name={`right-mode-${radioId}`}
              value="value"
              checked={rightMode === 'value'}
              onChange={() =>
                onChange({
                  ...condition,
                  right: { type: 'value', value: 0 },
                })
              }
              className="accent-accent"
            />
            Value
          </label>
          <label className="flex items-center gap-1 text-sm text-text-secondary cursor-pointer">
            <input
              type="radio"
              name={`right-mode-${radioId}`}
              value="indicator"
              checked={rightMode === 'indicator'}
              onChange={() =>
                onChange({
                  ...condition,
                  right: { type: 'indicator', indicator: '', params: {} },
                })
              }
              className="accent-accent"
            />
            Indicator
          </label>
        </div>

        {rightMode === 'value' ? (
          <input
            type="number"
            value={condition.right.value ?? 0}
            onChange={(e) =>
              updateRight({ value: parseFloat(e.target.value) })
            }
            className={`${inputClass} w-24`}
          />
        ) : (
          (() => {
            const rightDef = condition.right.indicator
              ? getIndicatorDef(indicators, condition.right.indicator)
              : undefined;
            return (
              <div className="flex items-center gap-2 flex-wrap">
                {renderIndicatorSelect(
                  condition.right,
                  (key) => {
                    const def = getIndicatorDef(indicators, key);
                    const defaultParams: Record<string, unknown> = {};
                    if (def) {
                      for (const p of def.params) {
                        defaultParams[p.name] = p.default;
                      }
                    }
                    updateRight({
                      type: 'indicator',
                      indicator: key,
                      params: defaultParams,
                      output: def && def.outputs.length > 1 ? def.outputs[0] : undefined,
                    });
                  },
                  false
                )}
                {rightDef && rightDef.outputs.length > 1 && (
                  <select
                    value={condition.right.output || rightDef.outputs[0]}
                    onChange={(e) => updateRight({ output: e.target.value })}
                    className={inputClass}
                  >
                    {rightDef.outputs.map((out) => (
                      <option key={out} value={out}>
                        {out}
                      </option>
                    ))}
                  </select>
                )}
                {rightDef && rightDef.params.map((param) => {
                  const currentValue =
                    condition.right.params?.[param.name] ?? param.default;

                  if (param.type === 'select' && param.options) {
                    return (
                      <label key={param.name} className="flex items-center gap-1">
                        <span className="text-sm text-text-secondary">{param.name}:</span>
                        <select
                          value={String(currentValue)}
                          onChange={(e) =>
                            updateRight({
                              params: {
                                ...condition.right.params,
                                [param.name]: e.target.value,
                              },
                            })
                          }
                          className={inputClass}
                        >
                          {param.options.map((opt) => (
                            <option key={opt} value={opt}>
                              {opt}
                            </option>
                          ))}
                        </select>
                      </label>
                    );
                  }

                  const step = param.type === 'float' ? 0.1 : 1;
                  return (
                    <label key={param.name} className="flex items-center gap-1">
                      <span className="text-sm text-text-secondary">{param.name}:</span>
                      <input
                        type="number"
                        value={currentValue as number}
                        step={step}
                        min={param.min}
                        max={param.max}
                        onChange={(e) =>
                          updateRight({
                            params: {
                              ...condition.right.params,
                              [param.name]:
                                param.type === 'int'
                                  ? parseInt(e.target.value, 10)
                                  : parseFloat(e.target.value),
                            },
                          })
                        }
                        className={`${inputClass} w-20`}
                      />
                    </label>
                  );
                })}
              </div>
            );
          })()
        )}
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2 flex-wrap p-3 bg-background rounded border border-border">
      {/* Left operand: indicator select */}
      <div className="flex items-start gap-2 flex-wrap">
        {renderIndicatorSelect(condition.left, handleLeftIndicatorChange, true)}
        {renderLeftParams()}
      </div>

      {/* Operator */}
      <OperatorSelect value={condition.operator} onChange={handleOperatorChange} />

      {/* Right operand */}
      {renderRightSide()}

      {/* Remove button */}
      <button
        type="button"
        onClick={onRemove}
        className="px-2 py-1.5 text-sm border border-border rounded hover:bg-surface-hover text-error ml-auto shrink-0"
        title="Remove condition"
      >
        &times;
      </button>
    </div>
  );
}
