# Builder Output — TASK-041a

## Task
Fix Strategy Validation Symbols Format

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
- `backend/app/strategies/validation.py` — Added list guard in `_validate_symbols` (line 297): returns early when symbols is a plain list, skipping mode/filter validation that assumes dict format. The `_validate_completeness` method (line 100) already had a list check.
- `backend/app/strategies/runner.py` — Added list guard in `_resolve_symbols` (line 466): returns the list directly when `symbols_config` is a plain list, before attempting `.get("mode")`.

## Files Deleted
None

## Acceptance Criteria Status
1. AC1: Saving a strategy with symbols as a list does not return 500 — ✅ Done (both validation.py and runner.py handle list format)
2. AC2: Saving a strategy with symbols as a dict still works — ✅ Done (list guard is an early return; dict path unchanged)
3. AC3: Validate and Enable buttons work after save — ✅ Done (validation no longer crashes on list symbols)
4. AC4: No other files assume symbols is a dict — ✅ Done (grep verified: all occurrences in validation.py and runner.py are guarded)
5. AC5: No frontend code modified — ✅ Done
6. AC6: Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
- A plain list of symbols is treated as mode "specific"/"explicit" — the list IS the symbol list
- No filter or watchlist validation is needed for list format since it's a direct symbol specification

## Ambiguities Encountered
None — task and specs were unambiguous

## Dependencies Discovered
None

## Tests Created
None — not required by this task

## Risks or Concerns
None identified

## Deferred Items
None — all deliverables complete

## Recommended Next Task
None — this was a targeted bug fix.
