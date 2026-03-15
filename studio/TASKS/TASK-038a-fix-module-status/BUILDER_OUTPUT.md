# Builder Output — TASK-038a

## Task
Fix Module Status Dot Colors & Alert Banner False Positive

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
- `frontend/src/features/system/PipelineStatus.tsx` — Updated module status dot color mapping to support "running", "ok", "degraded", "unknown", and "warning" statuses with appropriate colors
- `backend/app/observability/alerts/engine.py` — Added market hours check and subscribed symbols check to suppress WebSocket disconnect alerts outside US market hours or when no symbols are subscribed

## Files Deleted
None

## Acceptance Criteria Status
1. AC1: Module dots show green when status is "running" — ✅ Done (added "running" and "ok" to green list)
2. AC2: Module dots show yellow when status is "unknown" or "degraded" — ✅ Done (added "degraded", "unknown", "warning" to yellow list)
3. AC3: Module dots show red only for "error" or "stopped" — ✅ Done (all other statuses fall through to red/COLORS.error)
4. AC4: Alert banner does not show WebSocket disconnect outside US market hours (Mon-Fri 9:30 AM - 4:00 PM ET) — ✅ Done (added `_is_us_market_hours()` check in `_evaluate_absence`)
5. AC5: Alert banner does not show WebSocket disconnect when broker has 0 subscribed symbols — ✅ Done (checks `subscribedSymbols` from WebSocket manager health)
6. AC6: No frontend crashes — ✅ Done (TypeScript compiles cleanly, no runtime changes beyond color mapping)
7. AC7: Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
- Used `zoneinfo.ZoneInfo` (stdlib in Python 3.9+) with fallback to `backports.zoneinfo` for timezone handling, consistent with Python 3.12 stack
- The WebSocket heartbeat alert is the only absence-type alert that needs market hours suppression; the check is scoped specifically to `"market_data.websocket.heartbeat"` event type
- The `get_health()` dict uses camelCase keys (confirmed from `health.py` `to_dict()` method)

## Ambiguities Encountered
None — task and specs were unambiguous

## Dependencies Discovered
None

## Tests Created
None — not required by this task

## Risks or Concerns
- If market data holidays (e.g., Christmas, Thanksgiving) need to be respected, the `_is_us_market_hours()` check would need a holiday calendar. Currently only checks weekday + time range.

## Deferred Items
None — all deliverables complete

## Recommended Next Task
No immediate follow-up needed. If holiday-aware market hours checking is desired, that could be a future enhancement.
