interface DiffChange {
  field: string;
  oldValue: string;
  newValue: string;
  warning?: string;
}

interface StrategyDiffProps {
  oldVersion: number;
  newVersion: number;
  changes: DiffChange[];
}

export function StrategyDiff({
  oldVersion,
  newVersion,
  changes,
}: StrategyDiffProps) {
  if (changes.length === 0) {
    return null;
  }

  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <h3 className="text-text-primary text-sm font-medium mb-3">
        Changes (v{oldVersion} &rarr; v{newVersion})
      </h3>

      <div className="space-y-2">
        {changes.map((change, i) => (
          <div key={i}>
            <div className="flex items-baseline gap-3 text-sm">
              <span className="text-text-secondary min-w-[120px] shrink-0">
                {change.field}
              </span>
              <span className="text-error line-through">{change.oldValue}</span>
              <span className="text-text-tertiary">&rarr;</span>
              <span className="text-success">{change.newValue}</span>
            </div>

            {change.warning && (
              <div className="bg-warning/10 border border-warning/20 rounded mt-1 ml-[120px] px-3 py-1.5">
                <p className="text-warning text-sm">{change.warning}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
