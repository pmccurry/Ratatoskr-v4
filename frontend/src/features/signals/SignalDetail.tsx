interface SignalDetailProps {
  payloadJson: Record<string, unknown> | null;
}

export function SignalDetail({ payloadJson }: SignalDetailProps) {
  if (!payloadJson) {
    return (
      <div className="text-sm text-text-tertiary py-2">No payload data</div>
    );
  }

  return (
    <pre className="bg-background rounded p-3 text-xs font-mono text-text-secondary">
      {JSON.stringify(payloadJson, null, 2)}
    </pre>
  );
}
