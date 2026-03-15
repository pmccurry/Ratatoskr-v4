import type {
  Condition,
  ConditionGroup,
  IndicatorDefinition,
} from '@/types/strategy';
import { ConditionRow } from './ConditionRow';

interface ConditionBuilderProps {
  group: ConditionGroup;
  onChange: (group: ConditionGroup) => void;
  indicators: IndicatorDefinition[];
  label?: string;
}

function isConditionGroup(
  item: Condition | ConditionGroup
): item is ConditionGroup {
  return 'logic' in item && 'conditions' in item;
}

function makeEmptyCondition(): Condition {
  return {
    left: { type: 'indicator', indicator: '', params: {} },
    operator: 'greater_than',
    right: { type: 'value', value: 0 },
  };
}

function makeEmptyGroup(): ConditionGroup {
  return { logic: 'and', conditions: [] };
}

export function ConditionBuilder({
  group,
  onChange,
  indicators,
  label,
}: ConditionBuilderProps) {
  function toggleLogic() {
    onChange({ ...group, logic: group.logic === 'and' ? 'or' : 'and' });
  }

  function addCondition() {
    onChange({
      ...group,
      conditions: [...group.conditions, makeEmptyCondition()],
    });
  }

  function addGroup() {
    onChange({
      ...group,
      conditions: [...group.conditions, makeEmptyGroup()],
    });
  }

  function updateItem(index: number, item: Condition | ConditionGroup) {
    const updated = [...group.conditions];
    updated[index] = item;
    onChange({ ...group, conditions: updated });
  }

  function removeItem(index: number) {
    const updated = group.conditions.filter((_, i) => i !== index);
    onChange({ ...group, conditions: updated });
  }

  return (
    <div className="space-y-3">
      {/* Header: label + logic toggle */}
      <div className="flex items-center gap-3">
        {label && (
          <span className="text-sm font-medium text-text-primary">{label}</span>
        )}
        <button
          type="button"
          onClick={toggleLogic}
          className="px-3 py-1 text-sm font-medium rounded border border-border bg-surface hover:bg-surface-hover text-accent"
        >
          {group.logic.toUpperCase()}
        </button>
      </div>

      {/* Conditions and nested groups */}
      {group.conditions.length === 0 ? (
        <p className="text-sm text-text-tertiary py-2">
          No conditions added. Click "+ Add Condition" to begin.
        </p>
      ) : (
        <div className="space-y-2">
          {group.conditions.map((item, index) =>
            isConditionGroup(item) ? (
              <div
                key={index}
                className="ml-6 pl-4 border-l-2 border-border relative"
              >
                <button
                  type="button"
                  onClick={() => removeItem(index)}
                  className="absolute -left-3 top-0 px-1.5 py-0.5 text-xs border border-border rounded hover:bg-surface-hover text-error bg-surface"
                  title="Remove group"
                >
                  &times;
                </button>
                <ConditionBuilder
                  group={item}
                  onChange={(updated) => updateItem(index, updated)}
                  indicators={indicators}
                />
              </div>
            ) : (
              <ConditionRow
                key={index}
                condition={item}
                onChange={(updated) => updateItem(index, updated)}
                onRemove={() => removeItem(index)}
                indicators={indicators}
              />
            )
          )}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={addCondition}
          className="px-3 py-1.5 text-sm border border-border rounded hover:bg-surface-hover text-text-primary"
        >
          + Add Condition
        </button>
        <button
          type="button"
          onClick={addGroup}
          className="px-3 py-1.5 text-sm border border-border rounded hover:bg-surface-hover text-text-primary"
        >
          + Add Group
        </button>
      </div>
    </div>
  );
}
