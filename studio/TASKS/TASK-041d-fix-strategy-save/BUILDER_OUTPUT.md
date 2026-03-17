# Builder Output — TASK-041d

## Task
Fix Strategy Save Payload & Exit Validation

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
None

## Files Modified
- `frontend/src/pages/StrategyBuilder.tsx` — Fixed update mutation: wrapped config under `{ config: ... }` to match `UpdateStrategyConfigRequest` schema (was sending raw config object without wrapper)
- `backend/app/strategies/validation.py` — `_validate_completeness`: added fallback to `risk_management.stop_loss` and `risk_management.take_profit` when checking exit mechanisms. `_validate_risk_sanity`: added fallback to `risk_management.stop_loss` for SL percent validation.
- `backend/app/strategies/runner.py` — `_evaluate_exit`: added `risk_management` fallback for `stop_loss`, `take_profit`, and `trailing_stop` lookups so the runner finds SL/TP/trailing regardless of whether they're at the top level or nested under `risk_management`

## Files Deleted
None

## Acceptance Criteria Status
1. AC1: POST /api/v1/strategies succeeds when frontend sends strategy with all sections filled — ✅ Done (create path already sent `config` wrapper correctly; update path now fixed)
2. AC2: Config is properly nested under `config` key in the request body — ✅ Done (create: `buildPayload()` already correct; update: now sends `{ config: buildPayload().config }`)
3. AC3: Strategy with only risk_management SL/TP (no exit conditions) passes validation — ✅ Done (validator checks `risk_management.stop_loss` and `risk_management.take_profit` as fallback)
4. AC4: Strategy with only exit conditions (no SL/TP) still passes validation — ✅ Done (existing `exit_cond.get("conditions")` check unchanged)
5. AC5: Strategy with both exit conditions and SL/TP passes validation — ✅ Done (OR logic: any exit mechanism suffices)
6. AC6: Strategy with neither exit conditions nor SL/TP fails validation with clear error — ✅ Done (error: "At least one exit mechanism required")
7. AC7: Updating an existing strategy's config works — ✅ Done (PUT now sends `{ config: {...} }`)
8. AC8: Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
- The frontend nests SL/TP under `riskManagement` (which normalizes to `risk_management`). The backend supports both top-level `stop_loss`/`take_profit` keys and nested `risk_management.stop_loss`/`risk_management.take_profit`, with top-level taking precedence.
- The create path (`POST /strategies`) was already correct — `buildPayload()` includes the `config` wrapper. Only the update path (`PUT /strategies/{id}/config`) was missing it.

## Ambiguities Encountered
None

## Dependencies Discovered
None

## Tests Created
None — not required by this task

## Risks or Concerns
- The dual location for SL/TP (top-level vs risk_management) means configs could theoretically have conflicting values. Top-level takes precedence via the `or` fallback pattern.

## Deferred Items
None — all deliverables complete

## Recommended Next Task
None — this was a targeted bug fix.
