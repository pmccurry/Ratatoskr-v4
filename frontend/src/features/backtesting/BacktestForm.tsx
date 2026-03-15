import { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { runBacktest } from './backtestApi';
import type { BacktestParams, BacktestRun } from './backtestApi';

interface BacktestFormProps {
  strategyId: string;
  onComplete: (backtestId: string) => void;
}

const TIMEFRAMES = [
  { value: '1m', label: '1 Minute' },
  { value: '1h', label: '1 Hour' },
  { value: '4h', label: '4 Hours' },
  { value: '1d', label: '1 Day' },
];

const SIZING_TYPES = [
  { value: 'fixed_qty', label: 'Fixed Quantity' },
  { value: 'fixed_dollar', label: 'Fixed Dollar' },
  { value: 'percent_equity', label: '% of Equity' },
  { value: 'risk_based', label: 'Risk-Based' },
];

const selectClass =
  'w-full bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent';

const inputClass =
  'w-full bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary font-mono focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent';

function defaultDates(): { start: string; end: string } {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 90);
  return {
    start: start.toISOString().split('T')[0],
    end: end.toISOString().split('T')[0],
  };
}

export function BacktestForm({ strategyId, onComplete }: BacktestFormProps) {
  const dates = defaultDates();
  const [symbols, setSymbols] = useState('EUR_USD');
  const [timeframe, setTimeframe] = useState('1h');
  const [startDate, setStartDate] = useState(dates.start);
  const [endDate, setEndDate] = useState(dates.end);
  const [initialCapital, setInitialCapital] = useState(100000);
  const [sizingType, setSizingType] = useState('percent_equity');
  const [sizingAmount, setSizingAmount] = useState(2);
  const [stopLossPips, setStopLossPips] = useState<number | ''>('');
  const [takeProfitPips, setTakeProfitPips] = useState<number | ''>('');
  const [signalExit, setSignalExit] = useState(true);
  const [maxHoldBars, setMaxHoldBars] = useState<number | ''>('');
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const mutation = useMutation({
    mutationFn: (params: BacktestParams) => runBacktest(strategyId, params),
    onSuccess: (response) => {
      stopTimer();
      const run = response.data as BacktestRun;
      onComplete(run.id);
    },
    onError: () => {
      stopTimer();
    },
  });

  function startTimer() {
    setElapsed(0);
    timerRef.current = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);
  }

  function stopTimer() {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  useEffect(() => {
    return () => stopTimer();
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const positionSizing: BacktestParams['positionSizing'] = { type: sizingType };
    if (sizingType === 'fixed_qty' || sizingType === 'fixed_dollar') {
      positionSizing.amount = sizingAmount;
    } else if (sizingType === 'percent_equity') {
      positionSizing.percent = sizingAmount;
    } else if (sizingType === 'risk_based') {
      positionSizing.percent = sizingAmount;
    }

    const exitConfig: BacktestParams['exitConfig'] = {};
    if (stopLossPips !== '') exitConfig.stopLossPips = stopLossPips;
    if (takeProfitPips !== '') exitConfig.takeProfitPips = takeProfitPips;
    exitConfig.signalExit = signalExit;
    if (maxHoldBars !== '') exitConfig.maxHoldBars = maxHoldBars;

    const params: BacktestParams = {
      symbols: symbols.split(',').map((s) => s.trim()).filter(Boolean),
      timeframe,
      startDate,
      endDate,
      initialCapital,
      positionSizing,
      exitConfig,
    };

    startTimer();
    mutation.mutate(params);
  }

  const sizingLabel =
    sizingType === 'fixed_qty'
      ? 'Quantity'
      : sizingType === 'fixed_dollar'
        ? 'Dollar Amount'
        : sizingType === 'percent_equity'
          ? '% of Equity'
          : 'Risk %';

  return (
    <form onSubmit={handleSubmit} className="bg-surface border border-border rounded-lg p-4 space-y-4">
      <h3 className="text-sm font-medium text-text-primary">Backtest Configuration</h3>

      {/* Symbols */}
      <div className="grid grid-cols-3 gap-4 items-center">
        <label className="text-sm text-text-secondary">Symbols</label>
        <div className="col-span-2">
          <input
            type="text"
            value={symbols}
            onChange={(e) => setSymbols(e.target.value)}
            placeholder="EUR_USD, GBP_USD"
            className={inputClass}
          />
        </div>
      </div>

      {/* Timeframe */}
      <div className="grid grid-cols-3 gap-4 items-center">
        <label className="text-sm text-text-secondary">Timeframe</label>
        <div className="col-span-2">
          <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)} className={selectClass}>
            {TIMEFRAMES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Date Range */}
      <div className="grid grid-cols-3 gap-4 items-center">
        <label className="text-sm text-text-secondary">Start Date</label>
        <div className="col-span-2">
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className={inputClass} />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-4 items-center">
        <label className="text-sm text-text-secondary">End Date</label>
        <div className="col-span-2">
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className={inputClass} />
        </div>
      </div>

      {/* Initial Capital */}
      <div className="grid grid-cols-3 gap-4 items-center">
        <label className="text-sm text-text-secondary">Initial Capital</label>
        <div className="col-span-2">
          <input
            type="number"
            min={0}
            step="any"
            value={initialCapital}
            onChange={(e) => setInitialCapital(parseFloat(e.target.value) || 0)}
            className={inputClass}
          />
        </div>
      </div>

      {/* Position Sizing */}
      <div className="border-t border-border pt-4">
        <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wide mb-3">Position Sizing</h4>
        <div className="grid grid-cols-3 gap-4 items-center mb-3">
          <label className="text-sm text-text-secondary">Type</label>
          <div className="col-span-2">
            <select value={sizingType} onChange={(e) => setSizingType(e.target.value)} className={selectClass}>
              {SIZING_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 items-center">
          <label className="text-sm text-text-secondary">{sizingLabel}</label>
          <div className="col-span-2">
            <input
              type="number"
              min={0}
              step="any"
              value={sizingAmount}
              onChange={(e) => setSizingAmount(parseFloat(e.target.value) || 0)}
              className={inputClass}
            />
          </div>
        </div>
      </div>

      {/* Exit Config */}
      <div className="border-t border-border pt-4">
        <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wide mb-3">Exit Rules</h4>
        <div className="grid grid-cols-3 gap-4 items-center mb-3">
          <label className="text-sm text-text-secondary">Stop Loss (pips)</label>
          <div className="col-span-2">
            <input
              type="number"
              min={0}
              step="any"
              value={stopLossPips}
              onChange={(e) => setStopLossPips(e.target.value === '' ? '' : parseFloat(e.target.value))}
              placeholder="Optional"
              className={inputClass}
            />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 items-center mb-3">
          <label className="text-sm text-text-secondary">Take Profit (pips)</label>
          <div className="col-span-2">
            <input
              type="number"
              min={0}
              step="any"
              value={takeProfitPips}
              onChange={(e) => setTakeProfitPips(e.target.value === '' ? '' : parseFloat(e.target.value))}
              placeholder="Optional"
              className={inputClass}
            />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 items-center mb-3">
          <label className="text-sm text-text-secondary">Signal Exit</label>
          <div className="col-span-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={signalExit}
                onChange={(e) => setSignalExit(e.target.checked)}
                className="rounded border-border bg-surface text-accent focus:ring-accent"
              />
              <span className="text-sm text-text-primary">Exit on opposite signal</span>
            </label>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 items-center">
          <label className="text-sm text-text-secondary">Max Hold (bars)</label>
          <div className="col-span-2">
            <input
              type="number"
              min={0}
              step={1}
              value={maxHoldBars}
              onChange={(e) => setMaxHoldBars(e.target.value === '' ? '' : parseInt(e.target.value, 10))}
              placeholder="Optional"
              className={inputClass}
            />
          </div>
        </div>
      </div>

      {/* Error */}
      {mutation.isError && (
        <div className="bg-error/10 border border-error/30 rounded px-3 py-2 text-sm text-error">
          {typeof mutation.error === 'object' && mutation.error !== null && 'message' in mutation.error
            ? (mutation.error as { message: string }).message
            : 'Backtest failed. Check parameters and try again.'}
        </div>
      )}

      {/* Submit */}
      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          disabled={mutation.isPending}
          className="px-4 py-2 bg-accent text-white rounded hover:bg-accent/80 disabled:opacity-50 text-sm font-medium transition-colors"
        >
          {mutation.isPending ? 'Running...' : 'Run Backtest'}
        </button>
        {mutation.isPending && (
          <span className="text-sm text-text-secondary font-mono">{elapsed}s elapsed</span>
        )}
      </div>
    </form>
  );
}
