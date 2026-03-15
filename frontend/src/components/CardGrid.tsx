export function CardGrid({ children, columns = 4 }: { children: React.ReactNode; columns?: number }) {
  const gridCols: Record<number, string> = {
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4',
    5: 'grid-cols-5',
    6: 'grid-cols-6',
  };
  return (
    <div className={`grid gap-4 ${gridCols[columns] || 'grid-cols-4'}`}>
      {children}
    </div>
  );
}
