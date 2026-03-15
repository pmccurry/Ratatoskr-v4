import { useState, useRef, useEffect } from 'react';

interface DropdownItem {
  label: string;
  onClick: () => void;
  danger?: boolean;
}

interface DropdownMenuProps {
  trigger: React.ReactNode;
  items: DropdownItem[];
}

export function DropdownMenu({ trigger, items }: DropdownMenuProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <div onClick={() => setOpen(!open)}>{trigger}</div>
      {open && (
        <div className="absolute right-0 mt-1 bg-surface border border-border rounded-lg shadow-lg py-1 min-w-[160px] z-50">
          {items.map((item, i) => (
            <button
              key={i}
              onClick={() => { item.onClick(); setOpen(false); }}
              className={`w-full text-left px-4 py-2 text-sm hover:bg-surface-hover transition-colors ${
                item.danger ? 'text-error' : 'text-text-primary'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
