import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import api from '@/lib/api';
import { STALE } from '@/lib/constants';
import { PageContainer } from '@/components/PageContainer';
import { PageHeader } from '@/components/PageHeader';
import { SectionHeader, LoadingState } from '@/components';
import { ConditionBuilder } from '@/features/strategies/ConditionBuilder';
import { SymbolSelector } from '@/features/strategies/SymbolSelector';
import { RiskManagementForm } from '@/features/strategies/RiskManagementForm';
import { PositionSizingForm } from '@/features/strategies/PositionSizingForm';
import { ValidationSummary } from '@/features/strategies/ValidationSummary';
import { StrategyDiff } from '@/features/strategies/StrategyDiff';
import type { ConditionGroup, IndicatorDefinition, StrategyDetail } from '@/types/strategy';

const EMPTY_GROUP: ConditionGroup = { logic: 'and', conditions: [] };

interface FormState {
  name: string;
  description: string;
  market: string;
  timeframe: string;
  additionalTimeframes: string[];
  symbolMode: string;
  symbols: string[];
  symbolMarket: string;
  symbolFilters: { minVolume: string; minPrice: string };
  entryConditions: ConditionGroup;
  exitConditions: ConditionGroup;
  riskManagement: {
    stopLoss: { type: string; value: number };
    takeProfit: { type: string; value: number };
    trailingStop: { enabled: boolean; type: string; value: number };
    maxHoldBars: number | null;
  };
  positionSizing: { method: string; value: number; maxPositions: number; orderType: string };
  schedule: { tradingHours: string; reEntryCooldown: number };
}

const DEFAULT_FORM: FormState = {
  name: '',
  description: '',
  market: 'equities',
  timeframe: '1h',
  additionalTimeframes: [],
  symbolMode: 'explicit',
  symbols: [],
  symbolMarket: 'equities',
  symbolFilters: { minVolume: '', minPrice: '' },
  entryConditions: { ...EMPTY_GROUP },
  exitConditions: { ...EMPTY_GROUP },
  riskManagement: {
    stopLoss: { type: 'percent', value: 2 },
    takeProfit: { type: 'percent', value: 4 },
    trailingStop: { enabled: false, type: 'percent', value: 1 },
    maxHoldBars: null,
  },
  positionSizing: { method: 'percent_equity', value: 5, maxPositions: 3, orderType: 'market' },
  schedule: { tradingHours: 'regular', reEntryCooldown: 1 },
};

export default function StrategyBuilder() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = !!id;

  const [form, setForm] = useState<FormState>(DEFAULT_FORM);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [validationWarnings, setValidationWarnings] = useState<string[]>([]);
  const [validating, setValidating] = useState(false);
  const [showDiff, setShowDiff] = useState(false);
  const [diffChanges, setDiffChanges] = useState<Array<{ field: string; oldValue: string; newValue: string; warning?: string }>>([]);
  const validateTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { data: indicators, isLoading: indicatorsLoading } = useQuery<IndicatorDefinition[]>({
    queryKey: ['strategies', 'indicators'],
    queryFn: () => api.get('/strategies/indicators').then((r) => r.data),
    staleTime: STALE.indicatorCatalog,
  });

  const { data: existingStrategy, isLoading: strategyLoading } = useQuery<StrategyDetail>({
    queryKey: ['strategies', id],
    queryFn: () => api.get(`/strategies/${id}`).then((r) => r.data),
    enabled: isEdit,
    staleTime: STALE.strategyList,
  });

  useEffect(() => {
    if (existingStrategy) {
      const c = existingStrategy.config;
      setForm({
        name: existingStrategy.name,
        description: existingStrategy.description,
        market: existingStrategy.market,
        timeframe: c.timeframe,
        additionalTimeframes: [],
        symbolMode: 'explicit',
        symbols: c.symbols ?? [],
        symbolMarket: existingStrategy.market,
        symbolFilters: { minVolume: '', minPrice: '' },
        entryConditions: c.entryConditions ?? { ...EMPTY_GROUP },
        exitConditions: c.exitConditions ?? { ...EMPTY_GROUP },
        riskManagement: {
          stopLoss: (c.riskManagement as Record<string, unknown>)?.stopLoss as FormState['riskManagement']['stopLoss'] ?? { type: 'percent', value: 2 },
          takeProfit: (c.riskManagement as Record<string, unknown>)?.takeProfit as FormState['riskManagement']['takeProfit'] ?? { type: 'percent', value: 4 },
          trailingStop: (c.riskManagement as Record<string, unknown>)?.trailingStop as FormState['riskManagement']['trailingStop'] ?? { enabled: false, type: 'percent', value: 1 },
          maxHoldBars: (c.riskManagement as Record<string, unknown>)?.maxHoldBars as number | null ?? null,
        },
        positionSizing: {
          method: (c.positionSizing as Record<string, unknown>)?.method as string ?? 'percent_equity',
          value: (c.positionSizing as Record<string, unknown>)?.value as number ?? 5,
          maxPositions: (c.positionSizing as Record<string, unknown>)?.maxPositions as number ?? 3,
          orderType: (c.positionSizing as Record<string, unknown>)?.orderType as string ?? 'market',
        },
        schedule: {
          tradingHours: (c.schedule as Record<string, unknown>)?.tradingHours as string ?? 'regular',
          reEntryCooldown: (c.schedule as Record<string, unknown>)?.reEntryCooldown as number ?? 1,
        },
      });
    }
  }, [existingStrategy]);

  const buildPayload = useCallback(() => ({
    key: form.name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'untitled',
    name: form.name,
    description: form.description,
    market: form.market,
    config: {
      timeframe: form.timeframe,
      additionalTimeframes: form.additionalTimeframes,
      symbols: form.symbolMode === 'explicit' ? form.symbols : undefined,
      symbolMode: form.symbolMode,
      symbolMarket: form.symbolMode === 'watchlist' ? form.symbolMarket : undefined,
      symbolFilters: form.symbolMode === 'filtered' ? {
        minVolume: form.symbolFilters.minVolume ? parseInt(form.symbolFilters.minVolume) : undefined,
        minPrice: form.symbolFilters.minPrice ? parseFloat(form.symbolFilters.minPrice) : undefined,
      } : undefined,
      entryConditions: form.entryConditions,
      exitConditions: form.exitConditions,
      riskManagement: form.riskManagement,
      positionSizing: form.positionSizing,
      schedule: {
        tradingHours: form.schedule.tradingHours,
        reEntryCooldown: form.schedule.reEntryCooldown,
      },
    },
  }), [form]);

  const runValidation = useCallback(() => {
    // Client-side validation for immediate feedback
    const errors: string[] = [];
    const warnings: string[] = [];
    const payload = buildPayload();

    if (!payload.name.trim()) errors.push('Strategy name is required');
    if (!payload.config.symbols?.length && payload.config.symbolMode === 'explicit') {
      errors.push('At least one symbol is required for explicit symbol mode');
    }

    // Server-side validation only for existing strategies (endpoint requires strategy_id)
    if (isEdit && id) {
      setValidating(true);
      api.post(`/strategies/${id}/validate`, { config: payload.config })
        .then((r) => {
          const result = r.data?.data ?? r.data ?? r;
          const serverErrors = (result.errors ?? []).map((e: unknown) =>
            typeof e === 'string' ? e : (e as Record<string, string>)?.message ?? JSON.stringify(e)
          );
          const serverWarnings = (result.warnings ?? []).map((w: unknown) =>
            typeof w === 'string' ? w : (w as Record<string, string>)?.message ?? JSON.stringify(w)
          );
          setValidationErrors([...errors, ...serverErrors]);
          setValidationWarnings([...warnings, ...serverWarnings]);
        })
        .catch(() => {
          setValidationErrors(errors);
          setValidationWarnings(warnings);
        })
        .finally(() => setValidating(false));
    } else {
      setValidationErrors(errors);
      setValidationWarnings(warnings);
    }
  }, [buildPayload, isEdit, id]);

  useEffect(() => {
    if (validateTimer.current) clearTimeout(validateTimer.current);
    validateTimer.current = setTimeout(runValidation, 500);
    return () => { if (validateTimer.current) clearTimeout(validateTimer.current); };
  }, [form, runValidation]);

  const createMutation = useMutation({
    mutationFn: () => api.post('/strategies', buildPayload()),
    onSuccess: () => navigate('/strategies'),
  });

  const updateMutation = useMutation({
    mutationFn: () => api.put(`/strategies/${id}/config`, { config: buildPayload().config }),
    onSuccess: () => navigate(`/strategies/${id}`),
  });

  const enableMutation = useMutation({
    mutationFn: (strategyId: string) => api.post(`/strategies/${strategyId}/enable`),
    onSuccess: () => navigate('/strategies'),
  });

  const handleSaveDraft = () => createMutation.mutate();
  const handleEnable = async () => {
    if (isEdit) {
      enableMutation.mutate(id);
    } else {
      const res = await api.post('/strategies', buildPayload());
      const newId = (res.data ?? res).id;
      enableMutation.mutate(newId);
    }
  };

  const handleSaveAndApply = () => {
    if (existingStrategy && existingStrategy.status === 'enabled') {
      const changes: Array<{ field: string; oldValue: string; newValue: string; warning?: string }> = [];
      if (form.name !== existingStrategy.name) changes.push({ field: 'Name', oldValue: existingStrategy.name, newValue: form.name });
      if (form.timeframe !== existingStrategy.config.timeframe) changes.push({ field: 'Timeframe', oldValue: existingStrategy.config.timeframe, newValue: form.timeframe });
      const oldRm = existingStrategy.config.riskManagement as Record<string, unknown>;
      const oldSl = oldRm?.stopLoss as Record<string, unknown> | undefined;
      if (oldSl && form.riskManagement.stopLoss.value !== (oldSl.value as number)) {
        changes.push({ field: 'Stop Loss', oldValue: `${oldSl.value}`, newValue: `${form.riskManagement.stopLoss.value}`, warning: 'Stop loss change applies to existing positions' });
      }
      const oldTp = oldRm?.takeProfit as Record<string, unknown> | undefined;
      if (oldTp && form.riskManagement.takeProfit.value !== (oldTp.value as number)) {
        changes.push({ field: 'Take Profit', oldValue: `${oldTp.value}`, newValue: `${form.riskManagement.takeProfit.value}`, warning: 'Take profit change applies to existing positions' });
      }
      if (changes.length > 0) {
        setDiffChanges(changes);
        setShowDiff(true);
        return;
      }
    }
    updateMutation.mutate();
  };

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  if (isEdit && strategyLoading) return <PageContainer><LoadingState rows={8} /></PageContainer>;
  if (indicatorsLoading) return <PageContainer><LoadingState rows={8} /></PageContainer>;

  const indicatorList = indicators ?? [];
  const TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h'];

  return (
    <PageContainer>
      <PageHeader
        title={isEdit ? 'Edit Strategy' : 'New Strategy'}
        subtitle="Config-driven strategy builder"
      />

      <div className="max-w-4xl space-y-8">
        {/* 1. Identity */}
        <section className="bg-surface rounded-lg border border-border p-6 space-y-4">
          <SectionHeader title="Identity" />
          <div className="space-y-4">
            <div>
              <label className="text-sm text-text-secondary block mb-1">Name</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => update('name', e.target.value)}
                placeholder="Strategy name"
                className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary w-full focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>
            <div>
              <label className="text-sm text-text-secondary block mb-1">Description</label>
              <textarea
                value={form.description}
                onChange={(e) => update('description', e.target.value)}
                placeholder="Strategy description"
                rows={3}
                className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary w-full resize-none focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>
            <div>
              <label className="text-sm text-text-secondary block mb-1">Market</label>
              <div className="flex gap-4">
                {['equities', 'forex', 'both'].map((m) => (
                  <label key={m} className="flex items-center gap-2 text-sm text-text-primary cursor-pointer">
                    <input type="radio" name="market" value={m} checked={form.market === m} onChange={() => update('market', m)} className="accent-accent" />
                    {m.charAt(0).toUpperCase() + m.slice(1)}
                  </label>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-text-secondary block mb-1">Timeframe</label>
                <select
                  value={form.timeframe}
                  onChange={(e) => update('timeframe', e.target.value)}
                  className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary w-full focus:outline-none focus:ring-1 focus:ring-accent"
                >
                  {TIMEFRAMES.map((tf) => <option key={tf} value={tf}>{tf}</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm text-text-secondary block mb-1">Additional Timeframes</label>
                <div className="flex flex-wrap gap-2">
                  {TIMEFRAMES.filter((tf) => tf !== form.timeframe).map((tf) => (
                    <label key={tf} className="flex items-center gap-1 text-sm text-text-primary cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.additionalTimeframes.includes(tf)}
                        onChange={(e) => {
                          if (e.target.checked) update('additionalTimeframes', [...form.additionalTimeframes, tf]);
                          else update('additionalTimeframes', form.additionalTimeframes.filter((t) => t !== tf));
                        }}
                        className="accent-accent"
                      />
                      {tf}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* 2. Symbols */}
        <section className="bg-surface rounded-lg border border-border p-6 space-y-4">
          <SectionHeader title="Symbols" />
          <div className="flex gap-4 mb-4">
            {[
              { value: 'explicit', label: 'Specific' },
              { value: 'watchlist', label: 'Watchlist' },
              { value: 'filtered', label: 'Filtered' },
            ].map((opt) => (
              <label key={opt.value} className="flex items-center gap-2 text-sm text-text-primary cursor-pointer">
                <input type="radio" name="symbolMode" value={opt.value} checked={form.symbolMode === opt.value} onChange={() => update('symbolMode', opt.value)} className="accent-accent" />
                {opt.label}
              </label>
            ))}
          </div>
          {form.symbolMode === 'explicit' && (
            <SymbolSelector
              selected={form.symbols}
              onChange={(s: string[]) => update('symbols', s)}
              market={form.market !== 'both' ? form.market : undefined}
            />
          )}
          {form.symbolMode === 'watchlist' && (
            <div>
              <label className="text-sm text-text-secondary block mb-1">Market</label>
              <select
                value={form.symbolMarket}
                onChange={(e) => update('symbolMarket', e.target.value)}
                className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary w-full focus:outline-none focus:ring-1 focus:ring-accent"
              >
                <option value="equities">Equities</option>
                <option value="forex">Forex</option>
                <option value="all">All</option>
              </select>
            </div>
          )}
          {form.symbolMode === 'filtered' && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-text-secondary block mb-1">Min Volume</label>
                <input
                  type="number"
                  value={form.symbolFilters.minVolume}
                  onChange={(e) => update('symbolFilters', { ...form.symbolFilters, minVolume: e.target.value })}
                  placeholder="e.g., 1000000"
                  className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary w-full font-mono focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>
              <div>
                <label className="text-sm text-text-secondary block mb-1">Min Price</label>
                <input
                  type="number"
                  value={form.symbolFilters.minPrice}
                  onChange={(e) => update('symbolFilters', { ...form.symbolFilters, minPrice: e.target.value })}
                  placeholder="e.g., 5.00"
                  className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary w-full font-mono focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>
            </div>
          )}
        </section>

        {/* 3. Entry Conditions */}
        <section className="bg-surface rounded-lg border border-border p-6">
          <SectionHeader title="Entry Conditions" />
          <ConditionBuilder
            group={form.entryConditions}
            onChange={(g: ConditionGroup) => update('entryConditions', g)}
            indicators={indicatorList}
          />
        </section>

        {/* 4. Exit Conditions */}
        <section className="bg-surface rounded-lg border border-border p-6">
          <SectionHeader title="Exit Conditions" />
          <ConditionBuilder
            group={form.exitConditions}
            onChange={(g: ConditionGroup) => update('exitConditions', g)}
            indicators={indicatorList}
          />
        </section>

        {/* 5. Risk Management */}
        <section className="bg-surface rounded-lg border border-border p-6">
          <SectionHeader title="Risk Management" />
          <RiskManagementForm
            value={form.riskManagement}
            onChange={(v: FormState['riskManagement']) => update('riskManagement', v)}
          />
        </section>

        {/* 6. Position Sizing */}
        <section className="bg-surface rounded-lg border border-border p-6">
          <SectionHeader title="Position Sizing" />
          <PositionSizingForm
            value={form.positionSizing}
            onChange={(v: FormState['positionSizing']) => update('positionSizing', v)}
          />
        </section>

        {/* 7. Schedule */}
        <section className="bg-surface rounded-lg border border-border p-6 space-y-4">
          <SectionHeader title="Schedule" />
          <div>
            <label className="text-sm text-text-secondary block mb-1">Trading Hours</label>
            <div className="flex gap-4">
              {['regular', 'extended', 'custom'].map((m) => (
                <label key={m} className="flex items-center gap-2 text-sm text-text-primary cursor-pointer">
                  <input type="radio" name="tradingHours" value={m} checked={form.schedule.tradingHours === m} onChange={() => update('schedule', { ...form.schedule, tradingHours: m })} className="accent-accent" />
                  {m.charAt(0).toUpperCase() + m.slice(1)}
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="text-sm text-text-secondary block mb-1">Re-entry Cooldown (bars)</label>
            <input
              type="number"
              min={0}
              value={form.schedule.reEntryCooldown}
              onChange={(e) => update('schedule', { ...form.schedule, reEntryCooldown: parseInt(e.target.value) || 0 })}
              className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary w-32 font-mono focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>
        </section>

        {/* 8. Validation Summary */}
        <section>
          <ValidationSummary errors={validationErrors} warnings={validationWarnings} loading={validating} />
        </section>

        {/* 9. Actions */}
        <section className="flex gap-3 pb-8">
          {!isEdit && (
            <>
              <button
                onClick={handleSaveDraft}
                disabled={createMutation.isPending}
                className="px-4 py-2 text-sm border border-border rounded hover:bg-surface-hover text-text-primary disabled:opacity-50"
              >
                Save Draft
              </button>
              <button
                onClick={runValidation}
                className="px-4 py-2 text-sm border border-border rounded hover:bg-surface-hover text-text-primary"
              >
                Validate
              </button>
              <button
                onClick={handleEnable}
                disabled={validationErrors.length > 0 || enableMutation.isPending}
                className="px-4 py-2 text-sm bg-accent text-white rounded hover:bg-accent/80 disabled:opacity-50"
              >
                Enable
              </button>
            </>
          )}
          {isEdit && (
            <>
              {existingStrategy?.status === 'enabled' ? (
                <button
                  onClick={handleSaveAndApply}
                  disabled={validationErrors.length > 0 || updateMutation.isPending}
                  className="px-4 py-2 text-sm bg-accent text-white rounded hover:bg-accent/80 disabled:opacity-50"
                >
                  Save & Apply
                </button>
              ) : (
                <>
                  <button
                    onClick={() => updateMutation.mutate()}
                    disabled={updateMutation.isPending}
                    className="px-4 py-2 text-sm border border-border rounded hover:bg-surface-hover text-text-primary disabled:opacity-50"
                  >
                    Save
                  </button>
                  <button
                    onClick={handleEnable}
                    disabled={validationErrors.length > 0 || enableMutation.isPending}
                    className="px-4 py-2 text-sm bg-accent text-white rounded hover:bg-accent/80 disabled:opacity-50"
                  >
                    Enable
                  </button>
                </>
              )}
              <button
                onClick={runValidation}
                className="px-4 py-2 text-sm border border-border rounded hover:bg-surface-hover text-text-primary"
              >
                Validate
              </button>
            </>
          )}
        </section>

        {/* Diff dialog */}
        {showDiff && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowDiff(false)}>
            <div className="bg-surface border border-border rounded-lg p-6 w-[500px] space-y-4" onClick={(e) => e.stopPropagation()}>
              <StrategyDiff
                oldVersion={existingStrategy?.currentVersion ?? 0}
                newVersion={(existingStrategy?.currentVersion ?? 0) + 1}
                changes={diffChanges}
              />
              <div className="flex justify-end gap-2 pt-4">
                <button onClick={() => setShowDiff(false)} className="px-3 py-1.5 text-sm border border-border rounded hover:bg-surface-hover text-text-primary">Cancel</button>
                <button onClick={() => { setShowDiff(false); updateMutation.mutate(); }} className="px-3 py-1.5 text-sm bg-accent text-white rounded hover:bg-accent/80">Save & Apply</button>
              </div>
            </div>
          </div>
        )}
      </div>

      {(createMutation.isError || updateMutation.isError) && (
        <div className="fixed bottom-4 right-4 bg-error/10 border border-error/20 rounded-lg p-4 text-error text-sm">
          Failed to save strategy. Please try again.
        </div>
      )}
    </PageContainer>
  );
}
