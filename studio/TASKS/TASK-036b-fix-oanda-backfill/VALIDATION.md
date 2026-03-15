# Validation Report — TASK-036b

## Task
Fix OANDA Backfill Count Limit & DB Transaction Cascade

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
- [x] Files Created section present (None — appropriate)
- [x] Files Modified section present and non-empty
- [x] Files Deleted section present (None)
- [x] Acceptance Criteria Status — every criterion listed and marked
- [x] Assumptions section present
- [x] Ambiguities section present (explicit "None")
- [x] Dependencies section present (explicit "None")
- [x] Tests section present (excluded per task scope)
- [x] Risks section present (explicit "None")
- [x] Deferred Items section present (explicit "None")
- [x] Recommended Next Task section present

Section Result: PASS
Issues: None

---

## 2. Acceptance Criteria Verification

| # | Criterion | Builder Claims | Validator Verified | Status |
|---|-----------|---------------|-------------------|--------|
| AC1 | OANDA backfill never exceeds 5,000 candles per API call | Yes | Yes — `oanda.py:150` defines `_MAX_CANDLES = 5000`; line 161 passes `"count": _MAX_CANDLES` in params; `to` parameter removed, using `from` + `count` only | PASS |
| AC2 | Backfill paginates correctly for large ranges | Yes | Yes — `oanda.py:154` loops `while current_start < end`; line 200-203 advances `current_start` past last candle; line 181-183 filters candles past `end`; line 201-202 breaks on no progress; line 206-207 breaks when fewer than `_MAX_CANDLES` returned | PASS |
| AC3 | Failed backfill for one symbol doesn't prevent others | Yes | Yes — `runner.py:132-203`: each symbol/timeframe wrapped in `try/except`; outer except at line 201 logs error and continues loop | PASS |
| AC4 | Failed backfill doesn't poison DB session | Yes | Yes — `runner.py:133` creates isolated session via `session_factory()`; line 191 rolls back on error; lines 193-197 update job status in fresh transaction after rollback; original `db` session never used for writes | PASS |
| AC5 | OANDA startup completes successfully | Yes (code review) | Yes — pagination logic correct; session isolation prevents cascade. Live verification requires running backend. | PASS |
| AC6 | No frontend code modified | Yes | Yes — only `oanda.py` and `runner.py` modified | PASS |
| AC7 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) | Yes | Yes | PASS |

Section Result: PASS
Issues: None

---

## 3. Scope Check

- [x] No files created outside task deliverables
- [x] No files modified outside task scope (only `oanda.py` and `runner.py`)
- [x] No modules added that aren't in the approved list
- [x] No architectural changes or new patterns introduced
- [x] No live trading logic present
- [x] No dependencies added beyond what the task requires

Section Result: PASS
Issues: None

---

## 4. Naming Compliance

- [x] Python files use snake_case
- [x] Folder names match module specs exactly
- [x] Entity names match GLOSSARY exactly
- [x] Database-related names follow conventions
- [x] No typos in module or entity names

Section Result: PASS
Issues: None

---

## 5. Decision Compliance

- [x] No live trading logic (DECISION-002)
- [x] Tech stack matches approved stack (DECISIONS 007-009)
- [x] No Redis, microservices, or event bus
- [x] No off-scope modules (DECISION-001)
- [x] Python tooling uses uv (DECISION-010)
- [x] API is REST-first (DECISION-011)
- [x] Financial values use Decimal (convention) — `oanda.py:189-193` all use `Decimal(str(...))`

Section Result: PASS
Issues: None

---

## 6. Structure and Convention Compliance

- [x] Folder structure matches cross_cutting_specs and relevant module spec
- [x] File organization follows the defined module layout
- [x] No unexpected files in any directory

Section Result: PASS
Issues: None

---

## 7. Independent File Verification

### Files builder claims to have modified that ACTUALLY EXIST and are correct:

**`backend/app/market_data/adapters/oanda.py`** — Fix 1 verified:
- Line 150: `_MAX_CANDLES = 5000` constant defined
- Lines 158-163: params use `from` + `count` (no `to` parameter)
- Lines 172-183: candles past `end` are filtered out with `past_end` flag
- Lines 200-207: pagination advances `current_start`, breaks on no progress or fewer-than-max results
- Docstring at line 143 updated to document the 5,000 limit

**`backend/app/market_data/backfill/runner.py`** — Fix 2 verified:
- Line 115-116: imports `get_session_factory` from `app.common.database` (confirmed to exist at database.py:28)
- Line 133: each backfill uses `async with session_factory() as backfill_db:`
- Line 146: job creation committed immediately
- Line 183: successful bar upsert committed
- Lines 190-198: on error — rollback, update job status to "failed" with error message, commit in fresh transaction
- Lines 201-203: outer exception handler catches session-level errors, logs and continues

### Files that EXIST but builder DID NOT MENTION:
None

### Files builder claims to have modified that DO NOT EXIST:
None

Section Result: PASS
Issues: None

---

## Issues Summary

### Blockers (must fix before PASS)
None

### Major (should fix before proceeding)
None

### Minor (note for future, does not block)
1. **`needs_backfill()` still uses original `db` session** — `runner.py:125` calls `needs_backfill(db, ...)` with the startup session. This is a read-only check so it's safe, but if a previous backfill failure somehow affected the original session, this could fail. Low risk since the original `db` is only used for reads here.

2. **`backfill_gap()` doesn't have session isolation** — `runner.py:236-258` uses the caller's `db` session directly without isolation. If a gap backfill fails, it could poison the caller's session. This is acceptable since gap backfill is called from the WebSocket manager reconnect path (not startup), but worth noting for future hardening.

---

## Risk Notes
- The `retry_count += 1` at line 195 increments in-memory on the `job` object after rollback. Since the job was committed before the try block (line 146), the object is detached after rollback. The `backfill_db.add(job)` at line 196 re-attaches it, which should work correctly with SQLAlchemy's merge behavior, but this pattern could be fragile if the job had relationships.

---

## RESULT: PASS

Both fixes are correctly implemented. OANDA backfill now respects the 5,000 candle limit with proper pagination, and each symbol/timeframe backfill is isolated in its own DB session to prevent cascade failures. Task is ready for Librarian update.
