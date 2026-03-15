import { useState, useEffect } from 'react';
import api from '@/lib/api';
import type { Position } from '@/types/position';

interface EditStopLossDialogProps {
  open: boolean;
  position: Position | null;
  onClose: () => void;
  onSaved: () => void;
}

export function EditStopLossDialog({ open, position, onClose, onSaved }: EditStopLossDialogProps) {
  const [stopLoss, setStopLoss] = useState('');
  const [takeProfit, setTakeProfit] = useState('');

  useEffect(() => {
    if (open && position) {
      const pos = position as unknown as Record<string, unknown>;
      setStopLoss(pos.stopLoss != null ? String(pos.stopLoss) : '');
      setTakeProfit(pos.takeProfit != null ? String(pos.takeProfit) : '');
    }
  }, [open, position]);

  const handleSave = async () => {
    if (!position) return;
    await api.put(`/portfolio/positions/${position.id}/overrides`, {
      stopLoss: parseFloat(stopLoss) || null,
      takeProfit: parseFloat(takeProfit) || null,
    });
    onSaved();
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-surface rounded-lg border border-border p-6 w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-medium text-text-primary mb-4">
          Edit Stop Loss / Take Profit &mdash; {position?.symbol}
        </h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-text-secondary mb-1">Stop Loss</label>
            <input
              type="number"
              value={stopLoss}
              onChange={(e) => setStopLoss(e.target.value)}
              placeholder="Price..."
              className="bg-background border border-border rounded px-3 py-2 text-sm text-text-primary w-full font-mono"
            />
          </div>

          <div>
            <label className="block text-sm text-text-secondary mb-1">Take Profit</label>
            <input
              type="number"
              value={takeProfit}
              onChange={(e) => setTakeProfit(e.target.value)}
              placeholder="Price..."
              className="bg-background border border-border rounded px-3 py-2 text-sm text-text-primary w-full font-mono"
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="text-text-secondary hover:text-text-primary px-4 py-2 text-sm"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="bg-accent hover:bg-accent-hover text-white px-4 py-2 rounded text-sm"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
