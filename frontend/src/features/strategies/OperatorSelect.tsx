interface OperatorSelectProps {
  value: string;
  onChange: (operator: string) => void;
}

const OPERATOR_GROUPS = [
  {
    label: 'Comparison',
    operators: [
      { value: 'greater_than', label: '>' },
      { value: 'less_than', label: '<' },
      { value: 'greater_than_or_equal', label: '>=' },
      { value: 'less_than_or_equal', label: '<=' },
      { value: 'equal', label: '==' },
    ],
  },
  {
    label: 'Crossover',
    operators: [
      { value: 'crosses_above', label: 'Crosses Above' },
      { value: 'crosses_below', label: 'Crosses Below' },
    ],
  },
  {
    label: 'Range',
    operators: [
      { value: 'between', label: 'Between' },
      { value: 'outside', label: 'Outside' },
    ],
  },
];

export function OperatorSelect({ value, onChange }: OperatorSelectProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
    >
      {OPERATOR_GROUPS.map((group) => (
        <optgroup key={group.label} label={group.label}>
          {group.operators.map((op) => (
            <option key={op.value} value={op.value}>
              {op.label}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}
