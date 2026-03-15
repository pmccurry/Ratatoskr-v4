# Validation Report — TASK-036c

## Task
Fix Greenlet Spawn Error in Paginated Backfill

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
| AC1 | 1m backfill completes without greenlet_spawn error | Yes | Yes — `runner.py:148` captures `job_id = job.id` immediately after commit; lines 187-198 use raw `UPDATE` via `update(BackfillJob).where(BackfillJob.id == job_id).values(...)` instead of ORM attribute access; no stale ORM object accessed after the long fetch | PASS |
| AC2 | 1h backfill completes without greenlet_spawn error | Yes | Yes — same code path as 1m; fix applies to all timeframes equally | PASS |
| AC3 | 4h and 1d backfills continue to work (no regression) | Yes | Yes — same code path; raw UPDATE and batched upsert are compatible with small result sets | PASS |
| AC4 | Fix documented with root cause and before/after | Yes | Yes — BUILDER_OUTPUT.md contains detailed root cause analysis, trigger sequence, and before/after code for both changes | PASS |
| AC5 | No frontend code modified | Yes | Yes — only `runner.py` modified | PASS |
| AC6 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) | Yes | Yes | PASS |

Section Result: PASS
Issues: None

---

## 3. Scope Check

- [x] No files created outside task deliverables
- [x] No files modified outside task scope (only `runner.py`)
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
- [x] Financial values use Decimal — bar models at lines 169-172

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

**`backend/app/market_data/backfill/runner.py`** — Both fixes verified:

**Fix 1 — Raw UPDATE instead of ORM attribute access:**
- Line 148: `job_id = job.id` captured immediately after creation/commit
- Lines 187-198: Success path uses `await backfill_db.execute(update(BackfillJob).where(BackfillJob.id == job_id).values(...))` — no ORM object access after the long fetch
- Lines 205-223: Error path uses same raw UPDATE pattern after rollback; wrapped in inner try/except so job status update failure doesn't propagate
- Line 216: `retry_count=BackfillJob.retry_count + 1` uses SQLAlchemy column expression for atomic increment

**Fix 2 — Batched upsert:**
- Lines 179-184: `_BATCH_SIZE = 1000`; loop slices `bar_models` into batches of 1000 and calls `upsert_bars()` per batch
- Accumulates `count` across batches

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
1. **`from sqlalchemy import update` inside function body** — Lines 188 and 209 import `update` inside the try blocks. Could be moved to module-level imports for consistency with the rest of the file. Functionally correct but slightly unconventional.

2. **`backfill_gap()` still uses single upsert without batching** — Line 282 calls `upsert_bars(db, bar_models)` without batching. Gap backfills are typically small (minutes to hours of data), so this is acceptable, but worth noting for consistency.

---

## Risk Notes
- The inner try/except at line 220 with `pass` silently swallows job status update failures. This is acceptable since the job status is non-critical metadata, but it means a failed status update won't be visible in logs. The outer `logger.warning` at line 223 still fires for the original backfill error.

---

## RESULT: PASS

Single-file fix correctly addresses the greenlet_spawn error by replacing ORM object attribute access with raw SQL UPDATE statements, and adds batched upsert (1000 bars per batch) to prevent oversized INSERT statements. The `job_id` capture pattern at line 148 cleanly avoids any stale ORM object access after the long-running fetch. Task is ready for Librarian update.
