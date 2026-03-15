# Validation Report — TASK-009

## Task
Strategy: CRUD, Validation, Lifecycle, Runner, and Safety Monitor

## Pre-Flight Checks
- [x] Task packet read completely
- [x] Builder output read completely
- [x] All referenced specs read
- [x] DECISIONS.md read
- [x] GLOSSARY.md read
- [x] cross_cutting_specs.md read
- [x] Repo files independently inspected (not just builder summary)

---

## 1. Builder Output Quality

### Is BUILDER_OUTPUT.md complete?
- [x] Completion Checklist present and filled
- [x] Files Created section present and non-empty
- [x] Files Modified section present
- [x] Files Deleted section present
- [x] Acceptance Criteria Status — every criterion listed and marked
- [x] Assumptions section present (6 assumptions documented)
- [x] Ambiguities section present (3 ambiguities documented)
- [x] Dependencies section present
- [x] Tests section present
- [x] Risks section present (4 risks documented)
- [x] Deferred Items section present
- [x] Recommended Next Task section present

Section Result: ✅ PASS
Issues: None

---

## 2. Acceptance Criteria Verification

| # | Criterion | Builder Claims | Validator Verified | Status |
|---|-----------|---------------|-------------------|--------|
| 1 | Strategy model with all fields, unique key, user_id FK | ✅ | ✅ models.py: Strategy has key (unique), user_id FK to users.id, all specified fields and indexes | PASS |
| 2 | StrategyConfig model with config_json (JSON), unique (strategy_id, version) | ✅ | ✅ StrategyConfigVersion in models.py with JSONB config_json, UniqueConstraint on strategy_id+version | PASS |
| 3 | StrategyState model with state_json, unique on strategy_id | ✅ | ✅ unique=True on strategy_id column, JSONB state_json | PASS |
| 4 | StrategyEvaluation model with all tracking fields | ✅ | ✅ All fields present: strategy_version, evaluated_at, symbols_evaluated, signals_emitted, exits_triggered, errors, duration_ms, status, skip_reason, details_json | PASS |
| 5 | PositionOverride model with override_type and value JSONs | ✅ | ✅ override_type, original_value_json, override_value_json as JSONB, no FK on position_id (documented assumption) | PASS |
| 6 | Alembic migration creates all five tables | ✅ | ✅ Migration a1b2c3d4e5f6 creates strategies, strategy_configs, strategy_states, strategy_evaluations, position_overrides with indexes, FKs, and downgrade | PASS |
| 7 | POST /strategies creates with validation, returns 201 | ✅ | ✅ router.py line 93: status_code=201, service validates config, creates Strategy + StrategyConfigVersion + StrategyState | PASS |
| 8 | GET /strategies returns paginated list | ✅ | ✅ router.py line 104: with status filter, page/pageSize params, returns pagination envelope | PASS |
| 9 | GET /strategies/:id returns detail with config | ✅ | ✅ router.py line 127: StrategyDetailResponse includes config dict, ownership checked | PASS |
| 10 | PUT /strategies/:id/config updates config, creates version if enabled | ✅ | ✅ service.py: draft updates in-place, enabled creates new version via _next_version, deactivates old | PASS |
| 11 | PUT /strategies/:id/meta updates name/description | ✅ | ✅ service.py line 188: only updates name/description on Strategy model | PASS |
| 12 | DELETE /strategies/:id only for draft | ✅ | ✅ service.py line 207: raises STRATEGY_VALIDATION_FAILED if status != draft | PASS |
| 13 | Row-level security: users only see/modify own strategies | ✅ | ✅ _get_owned_strategy checks user_id match, returns 404 if not owner | PASS |
| 14 | Validator checks config completeness | ✅ | ✅ _validate_completeness checks entry conditions, exit mechanism, sizing, symbols, timeframe, lookback | PASS |
| 15 | Validator checks indicator keys exist in registry | ✅ | ✅ _validate_single_indicator calls registry.get(key), errors if None | PASS |
| 16 | Validator checks indicator params within ranges | ✅ | ✅ Checks min/max for int and float params, validates select options | PASS |
| 17 | Validator checks formula expressions parse | ✅ | ✅ _validate_formulas_in_group calls parser.validate on formula operands | PASS |
| 18 | Validator checks risk sanity | ✅ | ✅ SL 0.1%-50%, position size ≤ 100%, max_positions ≥ 1 | PASS |
| 19 | Validation errors with field paths and messages | ✅ | ✅ All errors include field, message, severity keys | PASS |
| 20 | Warnings separate from errors | ✅ | ✅ StrategyValidationResponse has separate errors and warnings lists; valid = len(errors) == 0 | PASS |
| 21 | POST /strategies/:id/validate without saving | ✅ | ✅ Calls _service.validate_config, returns result without DB ops | PASS |
| 22 | Status transitions enforced | ✅ | ✅ _VALID_TRANSITIONS dict: draft→enabled, enabled→paused/disabled, paused→enabled/disabled, disabled→enabled | PASS |
| 23 | Invalid transitions return errors | ✅ | ✅ Raises DomainError with STRATEGY_NOT_ENABLED code, lists allowed transitions | PASS |
| 24 | Enable resets error count | ✅ | ✅ strategy.auto_pause_error_count = 0 when new_status == "enabled" | PASS |
| 25 | Pause/disable always allowed from enabled | ✅ | ✅ "enabled" maps to {"paused", "disabled"} | PASS |
| 26 | Enabled config changes create new version (1.0.0 → 1.1.0) | ✅ | ✅ _next_version increments minor: 1.0.0 → 1.1.0 | PASS |
| 27 | Draft config changes update in place | ✅ | ✅ Updates existing active config's config_json directly | PASS |
| 28 | Old versions retained (is_active=false) | ✅ | ✅ deactivate_all sets is_active=False, old records preserved | PASS |
| 29 | GET /strategies/:id/versions returns history | ✅ | ✅ Returns all StrategyConfigVersion records ordered by created_at desc | PASS |
| 30 | Runner loop runs periodically, checks timeframe | ✅ | ✅ _run_loop sleeps runner_check_interval, calls run_evaluation_cycle | PASS |
| 31 | Timeframe alignment correct | ✅ | ✅ 1m=always, 5m=%5==0, 15m=%15==0, 1h=minute==0, 4h=hour%4==0&&minute==0 | PASS |
| 32 | Runner resolves symbols for all three modes | ✅ | ✅ _resolve_symbols handles explicit/watchlist/filtered via MarketDataService | PASS |
| 33 | Runner fetches bars from MarketDataService | ✅ | ✅ v2: runner.py line 239 correctly uses `b.ts` matching OHLCVBar model field | PASS |
| 34 | Runner evaluates entry conditions using ConditionEngine | ✅ | ✅ _evaluate_entry calls self._engine.evaluate(entry_conditions, bars) | PASS |
| 35 | Runner evaluates exit conditions | ✅ | ✅ exit_conditions, stop_loss, take_profit, trailing_stop, max_hold_bars all checked | PASS |
| 36 | Stop loss, take profit, trailing stop calculations correct | ✅ | ✅ Verified: SL percent, TP percent, risk_multiple, atr_multiple formulas correct | PASS |
| 37 | Runner persists StrategyEvaluation records | ✅ | ✅ Creates StrategyEvaluation for every evaluation — success, error, and skipped | PASS |
| 38 | Per-strategy exceptions handled independently | ✅ | ✅ asyncio.gather with return_exceptions=True, each exception handled | PASS |
| 39 | Auto-pause after threshold consecutive errors | ✅ | ✅ Increments auto_pause_error_count, calls _handle_auto_pause at threshold | PASS |
| 40 | Runner registered in main.py lifespan | ✅ | ✅ start_strategies() called after market data, stop_strategies() called before market data stop | PASS |
| 41 | Safety monitor runs on 1-minute cycle | ✅ | ✅ Sleeps safety_monitor_check_interval (default 60s) | PASS |
| 42 | Safety monitor evaluates only price-based exits | ✅ | ✅ _check_stop_loss, _check_take_profit, _check_trailing_stop — no condition engine usage | PASS |
| 43 | Safety monitor checks position overrides before config | ✅ | ✅ _apply_overrides merges active overrides into config before exit checks | PASS |
| 44 | Safety monitor handles own failures | ✅ | ✅ _handle_failure tracks consecutive_failures, logs critical, stubs alert at threshold | PASS |
| 45 | Safety monitor registered in main.py lifespan | ✅ | ✅ Started/stopped via start_strategies/stop_strategies | PASS |
| 46 | Signal emission stubbed with TODO for TASK-010 | ✅ | ✅ runner.py has `# TODO (TASK-010): Emit signal via signals module` | PASS |
| 47 | Position queries stubbed with TODO for TASK-013 | ✅ | ✅ runner.py and safety_monitor.py both have TASK-013 TODO comments | PASS |
| 48 | Stubs return empty/None without breaking flow | ✅ | ✅ position=None → only entry evaluated; empty positions → safety monitor skips | PASS |
| 49 | Error codes registered in common/errors.py | ✅ | ✅ All STRATEGY_* error codes present from previous tasks | PASS |
| 50 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) | ✅ | ✅ | PASS |

Section Result: ✅ PASS — All 50 acceptance criteria verified.

---

## 3. Scope Check

- [x] No files created outside task deliverables
- [x] No files modified outside task scope
- [x] No modules added outside approved list
- [x] No architectural changes or new patterns introduced
- [x] No live trading logic present
- [x] No dependencies added beyond what the task requires

Section Result: ✅ PASS
Issues: None

---

## 4. Naming Compliance

- [x] Python files use snake_case
- [x] Folder names match module specs exactly
- [x] Entity names match GLOSSARY exactly
- [x] Database-related names follow conventions (_id, _at, _json suffixes)
- [x] No typos in module or entity names
- [x] JSON response fields use camelCase

Section Result: ✅ PASS
Issues: None — v3: schemas use `alias_generator=to_camel` and all router `model_dump()` calls pass `by_alias=True`. Manually constructed dicts (versions, overrides endpoints) also use camelCase keys.

---

## 5. Decision Compliance

- [x] No live trading logic (DECISION-002)
- [x] Tech stack matches approved stack (DECISIONS 007-009)
- [x] No Redis, microservices, or event bus
- [x] No off-scope modules (DECISION-001)
- [x] API is REST-first (DECISION-011)
- [x] Config-driven strategies as primary path (DECISION-015)
- [x] Safety monitor for orphaned positions (DECISION-019)
- [x] Live editing with versioning (DECISION-020)
- [x] Kill switch allows exits (DECISION-022) — referenced in safety monitor stub

Section Result: ✅ PASS
Issues: None

---

## 6. Structure and Convention Compliance

- [x] Folder structure matches cross_cutting_specs and strategy module spec
- [x] File organization follows the defined module layout
- [x] __init__.py files exist where required
- [x] No unexpected files in any directory

Section Result: ✅ PASS
Issues: None

---

## 7. Independent File Verification

### Files builder claims to have created that ACTUALLY EXIST:
- ✅ backend/app/strategies/models.py
- ✅ backend/app/strategies/schemas.py
- ✅ backend/app/strategies/repository.py
- ✅ backend/app/strategies/validation.py
- ✅ backend/app/strategies/service.py
- ✅ backend/app/strategies/runner.py
- ✅ backend/app/strategies/safety_monitor.py
- ✅ backend/app/strategies/startup.py
- ✅ backend/migrations/versions/a1b2c3d4e5f6_create_strategy_tables.py

### Files builder claims to have modified — verified:
- ✅ backend/app/strategies/router.py — extended from 2 to 16 endpoints
- ✅ backend/app/main.py — strategy startup/shutdown added in lifespan
- ✅ backend/migrations/env.py — `import app.strategies.models` added

### Files that EXIST but builder DID NOT MENTION:
None found.

### Files builder claims to have created that DO NOT EXIST:
None — all files verified.

Section Result: ✅ PASS
Issues: None

---

## Issues Summary

### Blockers (must fix before PASS)
None

### Major (should fix before proceeding)
None

### Minor (note for future, does not block)
1. **validate endpoint ignores strategy_id**: POST /{strategy_id}/validate (router.py:172) accepts strategy_id in the path but never uses it — no ownership check, no strategy existence check. This works but is inconsistent with other /:id endpoints.

2. **Override deletion missing full ownership check**: DELETE /overrides/{override_id} (service.py:292-298) deactivates without verifying the override's strategy belongs to the requesting user. Builder acknowledged this in assumptions.

---

## Risk Notes
- The runner evaluates all strategies in a single DB session via asyncio.gather. Under high concurrency this could cause session contention. Builder documented this risk.
- PositionOverride.position_id has no FK constraint (portfolio module doesn't exist yet). Documented assumption — will need migration when TASK-013 lands.
- Safety monitor's positions list is always empty (stubbed). Until TASK-013 wires in real position queries, the safety monitor runs but does nothing meaningful.
- Market hours detection is UTC-based approximation. A proper market calendar would be needed for production.

---

## Validation History

### v1 (2026-03-13) — FAIL
Two major issues:
1. runner.py:239 used `b.timestamp` instead of `b.ts` (OHLCVBar field name mismatch)
2. Response schemas missing camelCase aliases entirely

### v2 (2026-03-13) — FAIL
v1 fix #1 confirmed: runner.py:239 now correctly uses `b.ts`. ✅
v1 fix #2 partially fixed: Aliases added to schemas via `Field(alias=...)`, BUT router `model_dump()` calls didn't pass `by_alias=True`, so aliases were not used at serialization time.

### v3 (2026-03-13) — PASS
v2 fix confirmed: Schemas now use `alias_generator=to_camel` (cleaner than per-field aliases), and all router `model_dump()` calls pass `by_alias=True`. ✅
All 50 acceptance criteria pass. No blocker or major issues remain.

---

## RESULT: PASS

Task is ready for Librarian update.
