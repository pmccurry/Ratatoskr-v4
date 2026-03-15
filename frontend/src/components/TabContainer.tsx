import { useState } from 'react';

interface Tab {
  key: string;
  label: string;
}

interface TabContainerProps {
  tabs: Tab[];
  defaultTab?: string;
  onTabChange?: (tab: string) => void;
  children: (activeTab: string) => React.ReactNode;
}

export function TabContainer({ tabs, defaultTab, onTabChange, children }: TabContainerProps) {
  const [active, setActive] = useState(defaultTab || tabs[0]?.key || '');
  return (
    <div>
      <div className="flex gap-1 border-b border-border mb-4">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => { setActive(tab.key); onTabChange?.(tab.key); }}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              active === tab.key
                ? 'text-accent border-b-2 border-accent'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {children(active)}
    </div>
  );
}
