interface SectionHeaderProps {
  title: string;
  action?: React.ReactNode;
}

export function SectionHeader({ title, action }: SectionHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h2 className="text-lg font-medium text-text-primary">{title}</h2>
      {action && <div>{action}</div>}
    </div>
  );
}
