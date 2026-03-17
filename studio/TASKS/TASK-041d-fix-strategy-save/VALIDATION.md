# Validation Report — TASK-041d

## Task
Fix Strategy Save Payload & Exit Validation

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
- [x] Files Created section present (None — correct)
- [x] Files Modified section present — 3 files listed
- [x] Files Deleted section present (None — correct)
- [x] Acceptance Criteria Status — all 8 criteria listed and marked
- [x] Assumptions section present — dual-location SL/TP precedence documented
- [x] Ambiguities section present
- [x] Dependencies section present
- [x] Tests section present
- [x] Risks section present — conflicting SL/TP values noted
- [x] Deferred Items section present
- [x] Recommended Next Task section present

Section Result: ✅ PASS
Issues: None

---

## 2. Acceptance Criteria Verification

| # | Criterion | Builder Claims | Validator Verified | Status |
|---|-----------|---------------|-------------------|--------|
| 1 | POST /api/v1/strategies succeeds when frontend sends strategy with all sections filled | ✅ | ✅ `buildPayload()` (StrategyBuilder.tsx:124-148) returns `{ key, name, description, market, config: {...} }` — correctly structured. `api.post('/strategies', buildPayload())` at line 194. | PASS |
| 2 | Config is properly nested under `config` key in the request body | ✅ | ✅ Create path (line 194): sends full payload with `config` wrapper. Update path (line 199): `{ config: buildPayload().config }`. Validate path (line 164): `{ config: payload.config }`. All correct. | PASS |
| 3 | Strategy with only risk_management SL/TP (no exit conditions) passes validation | ✅ | ✅ validation.py:93-97: `risk_mgmt = config.get("risk_management", {}) or {}` then falls back to `risk_mgmt.get("stop_loss")` and `risk_mgmt.get("take_profit")` when top-level keys are absent. These are checked in `has_exit` at lines 98-102. | PASS |
| 4 | Strategy with only exit conditions (no SL/TP) still passes validation | ✅ | ✅ Line 99: `exit_cond and exit_cond.get("conditions")` check is first in the OR chain, unchanged from before. | PASS |
| 5 | Strategy with both exit conditions and SL/TP passes validation | ✅ | ✅ OR logic at lines 98-102: any truthy branch suffices. | PASS |
| 6 | Strategy with neither exit conditions nor SL/TP fails validation with clear error | ✅ | ✅ Lines 103-108: error "At least one exit mechanism required" when `has_exit` is False. | PASS |
| 7 | Updating an existing strategy's config works | ✅ | ✅ Line 199: `api.put(\`/strategies/${id}/config\`, { config: buildPayload().config })` — sends wrapped config. | PASS |
| 8 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) | ✅ | ✅ `git diff --name-only HEAD` shows only: `backend/app/strategies/runner.py`, `backend/app/strategies/validation.py`, `frontend/src/pages/StrategyBuilder.tsx`. | PASS |

Section Result: ✅ PASS
Issues: None

---

## 3. Scope Check

- [x] No files created outside task deliverables
- [x] No files modified outside task scope (3 files: frontend save, backend validation, backend runner)
- [x] No modules added that aren't in the approved list
- [x] No architectural changes or new patterns introduced
- [x] No live trading logic present
- [x] No dependencies added beyond what the task requires

Section Result: ✅ PASS
Issues: None

---

## 4. Naming Compliance

- [x] Python files use snake_case
- [x] TypeScript component files use PascalCase
- [x] No new entities or folders created
- [x] Existing naming conventions maintained

Section Result: ✅ PASS
Issues: None

---

## 5. Decision Compliance

- [x] No live trading logic (DECISION-002)
- [x] Tech stack unchanged (DECISIONS 007-009)
- [x] No Redis, microservices, or event bus
- [x] No off-scope modules (DECISION-001)
- [x] JSON/TypeScript uses camelCase, Python uses snake_case (data conventions)

Section Result: ✅ PASS
Issues: None

---

## 6. Structure and Convention Compliance

- [x] No structural changes — only in-place edits to existing files
- [x] File organization unchanged
- [x] No new directories
- [x] No unexpected files

Section Result: ✅ PASS
Issues: None

---

## 7. Independent File Verification

### Files builder claims to have modified that ACTUALLY EXIST and contain changes:
- `frontend/src/pages/StrategyBuilder.tsx` — ✅ Confirmed. Create path at line 194 sends `buildPayload()` with config wrapper. Update path at line 199 sends `{ config: buildPayload().config }`. Validate path at line 164 sends `{ config: payload.config }`.
- `backend/app/strategies/validation.py` — ✅ Confirmed. `_validate_completeness` at lines 92-97: falls back to `risk_management.stop_loss` and `risk_management.take_profit`. `_validate_risk_sanity` at lines 359-360: falls back to `risk_mgmt.get("stop_loss")`.
- `backend/app/strategies/runner.py` — ✅ Confirmed. `_evaluate_exit` at lines 549-553: resolves `risk_management` fallback for `stop_loss`. Line 569: fallback for `take_profit`. Line 585: fallback for `trailing_stop`.

### Files that EXIST but builder DID NOT MENTION:
None

### Files builder claims to have modified that DO NOT EXIST:
None

Section Result: ✅ PASS
Issues: None

---

## Issues Summary

### Blockers (must fix before PASS)
None

### Major (should fix before proceeding)
None

### Minor (note for future, does not block)
None

---

## Risk Notes
- **Safety monitor gap:** `safety_monitor.py` methods `_check_stop_loss` (line 245), `_check_take_profit` (line 269), and `_check_trailing_stop` (line 293) still only look for top-level `stop_loss`/`take_profit`/`trailing_stop` config keys. They do not check `risk_management.*` as a fallback. If a strategy config stores SL/TP only under `risk_management`, the safety monitor will not find them for orphaned positions. This is outside the explicit scope of TASK-041d (which targeted validation and the runner), but should be addressed in a follow-up task to ensure consistent behavior across all config consumers.
- **Dual-location precedence:** The `or` pattern (`config.get("stop_loss") or risk_mgmt.get("stop_loss")`) means top-level takes precedence. If both exist with different values, the top-level wins silently. Builder correctly documented this risk.

---

## RESULT: PASS

Task is ready for Librarian update. The safety monitor `risk_management` fallback gap should be tracked as a follow-up item.
