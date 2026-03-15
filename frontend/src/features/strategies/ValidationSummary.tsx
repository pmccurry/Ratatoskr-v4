interface ValidationSummaryProps {
  errors: string[];
  warnings: string[];
  loading?: boolean;
}

export function ValidationSummary({
  errors,
  warnings,
  loading,
}: ValidationSummaryProps) {
  if (loading) {
    return (
      <div className="bg-surface border border-border rounded-lg p-4 animate-pulse">
        <div className="h-4 bg-text-tertiary/20 rounded w-1/3 mb-2" />
        <div className="h-3 bg-text-tertiary/20 rounded w-2/3" />
      </div>
    );
  }

  const hasErrors = errors.length > 0;
  const hasWarnings = warnings.length > 0;

  if (!hasErrors && !hasWarnings) {
    return (
      <div className="bg-success/10 border border-success/20 rounded-lg p-4">
        <p className="text-success text-sm font-medium">Validation passed</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {hasErrors && (
        <div className="bg-error/10 border border-error/20 rounded-lg p-4">
          <p className="text-error text-sm font-medium mb-2">
            {errors.length} {errors.length === 1 ? 'error' : 'errors'}
          </p>
          <ul className="space-y-1">
            {errors.map((error, i) => (
              <li key={i} className="text-error text-sm flex items-start gap-2">
                <span className="mt-0.5 shrink-0">&bull;</span>
                <span>{error}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {hasWarnings && (
        <div className="bg-warning/10 border border-warning/20 rounded-lg p-4">
          <p className="text-warning text-sm font-medium mb-2">
            {warnings.length} {warnings.length === 1 ? 'warning' : 'warnings'}
          </p>
          <ul className="space-y-1">
            {warnings.map((warning, i) => (
              <li key={i} className="text-warning text-sm flex items-start gap-2">
                <span className="mt-0.5 shrink-0">&bull;</span>
                <span>{warning}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
