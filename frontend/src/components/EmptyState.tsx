interface EmptyStateProps {
  message: string;
  action?: { label: string; onClick: () => void };
}

export function EmptyState({ message, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-text-tertiary">
      <p className="text-sm">{message}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 px-4 py-2 bg-accent hover:bg-accent-hover text-white text-sm rounded transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
