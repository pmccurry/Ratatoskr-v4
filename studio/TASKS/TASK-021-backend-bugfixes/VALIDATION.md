# Validation Report — TASK-021

## Task
Backend Bug Fixes

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
- [x] Files Created section present and non-empty (explicitly "None")
- [x] Files Modified section present
- [x] Files Deleted section present
- [x] Acceptance Criteria Status — every criterion listed and marked
- [x] Assumptions section present (4 assumptions documented)
- [x] Ambiguities section present (explicit "None")
- [x] Dependencies section present
- [x] Tests section present
- [x] Risks section present (2 risks documented)
- [x] Deferred Items section present
- [x] Recommended Next Task section present

Section Result: ✅ PASS
Issues: None

---

## 2. Acceptance Criteria Verification

| # | Criterion | Builder Claims | Validator Verified | Status |
|---|-----------|---------------|-------------------|--------|
| 1 | FIX-B1: Options expiration PnL entry has correct qty_closed (not zero) | ✅ | ✅ `qty_at_expiry = position.qty` captured at line 76 before `position.qty = Decimal("0")` at line 79; `qty_closed=qty_at_expiry` at line 109 | PASS |
| 2 | FIX-B2: Paper trading updates signal status through SignalService (not direct write) | ✅ | ✅ `_update_signal_status()` method at lines 405-421 imports `get_signal_service()` and calls `signal_service.update_signal_status()`. All signal status updates route through this method. | PASS |
| 3 | FIX-B2: Signal module accepts transitions: risk_approved/risk_modified -> order_filled/order_rejected | ✅ | ✅ `_VALID_TRANSITIONS` dict at lines 21-25 includes `"risk_approved": {"order_filled", "order_rejected"}` and `"risk_modified": {"order_filled", "order_rejected"}` | PASS |
| 4 | FIX-B3: DrawdownMonitor reads peak equity from portfolio service only (no in-memory fallback) | ✅ | ✅ No `_peak_equity` instance variable. `_get_peak_equity()` reads from `PortfolioMetaRepository` (lines 118-142). `_get_current_equity()` reads from portfolio service (lines 95-116). | PASS |
| 5 | FIX-B3: DrawdownMonitor returns "degraded" status if portfolio service unavailable | ✅ | ✅ Lines 29-37: when `not equity_available or not peak_available`, returns dict with `"threshold_status": "degraded"` | PASS |
| 6 | FIX-B4: DailyPortfolioJobs runs automatically after market close on new trading days | ✅ | ✅ `_check_daily_jobs()` at lines 201-230 creates `DailyPortfolioJobs()` and calls `run_daily(db, user_id)` for each user after `_MARKET_CLOSE_HOUR_UTC = 21` | PASS |
| 7 | FIX-B4: Trading day detection integrated into snapshot periodic loop | ✅ | ✅ `_check_daily_jobs()` called at line 188 in `_run_loop()` after periodic snapshots complete | PASS |
| 8 | FIX-B6: Cash manager includes estimated fee in required cash for buy orders | ✅ | ✅ `_estimate_fee()` at lines 83-90 computes fee by market type. `calculate_required_cash()` at line 81 returns `gross + estimated_fee` for buy orders (sells return 0 at line 76). | PASS |
| 9 | FIX-B7: Sortino ratio has clarifying comment about denominator convention | ✅ | ✅ Lines 226-229 in metrics.py: comment explains downside_dev uses ALL returns in denominator (N = total periods). Code at line 236 correctly divides by `n` (total returns count). | PASS |
| 10 | FIX-B8: Exposure checks use actual proposed position value (not estimated from limit) | ✅ | ✅ All three checks use `context.proposed_position_value`: SymbolExposureCheck (exposure.py:26), StrategyExposureCheck (exposure.py:69), PortfolioExposureCheck (exposure.py:97) | PASS |
| 11 | FIX-B8: RiskContext includes proposed_position_value field | ✅ | ✅ `proposed_position_value: Decimal` at base.py:44 with comment `# qty * price * multiplier` | PASS |
| 12 | No new features or modules created | ✅ | ✅ Files Created = None. No new modules. All changes are targeted bug fixes. | PASS |
| 13 | No frontend code modified | ✅ | ✅ No frontend files appear in modified list. Git status confirms no staged frontend changes. | PASS |
| 14 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) | ✅ | ✅ Only BUILDER_OUTPUT.md written in /studio/TASKS/TASK-021-backend-bugfixes/ | PASS |

Section Result: ✅ PASS
Issues: None

---

## 3. Scope Check

- [x] No files created outside task deliverables
- [x] No files modified outside task scope
- [x] No modules added that aren't in the approved list
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
- [x] Database-related names follow conventions
- [x] No typos in module or entity names
- N/A TypeScript files (no frontend changes)

Section Result: ✅ PASS
Issues: None

---

## 5. Decision Compliance

- [x] No live trading logic (DECISION-002)
- [x] Tech stack matches approved stack (DECISIONS 007-009)
- [x] No Redis, microservices, or event bus
- [x] No off-scope modules (DECISION-001)
- [x] API is REST-first (DECISION-011)

Section Result: ✅ PASS
Issues: None

---

## 6. Structure and Convention Compliance

- [x] Folder structure matches cross_cutting_specs and relevant module specs
- [x] File organization follows the defined module layout
- [x] No unexpected files in any directory

Section Result: ✅ PASS
Issues: None

---

## 7. Independent File Verification

### Files builder claims to have created that ACTUALLY EXIST:
None claimed, none expected.

### Files builder claims to have modified — independently verified:
1. `backend/app/portfolio/options_lifecycle.py` — ✅ verified (FIX-B1: qty_at_expiry pattern)
2. `backend/app/signals/service.py` — ✅ verified (FIX-B2: valid transitions added)
3. `backend/app/paper_trading/service.py` — ✅ verified (FIX-B2: uses SignalService for status updates)
4. `backend/app/risk/monitoring/drawdown.py` — ✅ verified (FIX-B3: no in-memory fallback, degraded status)
5. `backend/app/portfolio/snapshots.py` — ✅ verified (FIX-B4: _check_daily_jobs in periodic loop)
6. `backend/app/paper_trading/cash_manager.py` — ✅ verified (FIX-B6: _estimate_fee included)
7. `backend/app/portfolio/metrics.py` — ✅ verified (FIX-B7: clarifying comment on Sortino)
8. `backend/app/risk/checks/base.py` — ✅ verified (FIX-B8: proposed_position_value field)
9. `backend/app/risk/checks/exposure.py` — ✅ verified (FIX-B8: all 3 checks use proposed_position_value)
10. `backend/app/risk/service.py` — ✅ verified (FIX-B8: _build_context populates proposed_position_value)

### Files that EXIST but builder DID NOT MENTION:
None found.

### Files builder claims to have created that DO NOT EXIST:
N/A (no files claimed created).

Section Result: ✅ PASS
Issues: None

---

## Issues Summary

### Blockers (must fix before PASS)
None

### Major (should fix before proceeding)
None

### Minor (note for future, does not block)

1. **DrawdownMonitor admin user lookup pattern**: `_get_peak_equity()`, `_get_current_equity()`, and `reset_peak_equity()` all independently query `select(User.id).where(User.role == "admin").limit(1)` to find a user_id. This repeats the same query pattern 3 times within one file and assumes a single admin user exists. Not a bug but a fragile pattern — if no admin user exists, peak equity and current equity lookups silently fail to `(False, default)`.

2. **DailyPortfolioJobs instantiated per check**: `_check_daily_jobs()` creates a new `DailyPortfolioJobs()` instance on every invocation (line 216) rather than caching it. Minor inefficiency — the method only runs once per day, so the impact is negligible.

3. **Market close hour hardcoded**: `_MARKET_CLOSE_HOUR_UTC = 21` is hardcoded. Builder documented this as an assumption (21:00 UTC = 4 PM EST, but during EDT market close is 20:00 UTC). Daily jobs may run ~1 hour late during summer. Acceptable for now but noted for future configurability.

4. **Proposed position value fallback to strategy config**: When `signal.requested_qty` is None (which is always, per builder's assumption #3 that signals don't carry qty), `_build_context()` estimates from strategy config position sizing. This is a reasonable fallback but means the "actual proposed value" is still an estimate — just a better one than the old percentage-of-limit approach.

---

## Risk Notes

- The DrawdownMonitor's "degraded" status path needs downstream consumers (risk service auto-kill-switch, risk dashboard) to handle it correctly. The risk service's catastrophic check at `risk/service.py:552` only triggers on `"catastrophic"`, so "degraded" correctly avoids false kill switch activation.
- The `_update_signal_status()` method in `paper_trading/service.py` (lines 405-421) catches exceptions silently with `logger.warning`. If the signal service is unavailable, the fill proceeds but the signal status is not updated. This is existing behavior, not introduced by this task.

---

## RESULT: PASS

All 14 acceptance criteria independently verified against actual code. All 8 bug fixes (B1-B4, B6-B8, B5=B2) are correctly implemented with minimal, targeted changes. No frontend modifications, no new features, no scope creep. Task is ready for Librarian update.
