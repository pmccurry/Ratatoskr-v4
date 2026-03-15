# WORKFLOW PROTOCOL

## Purpose
This document defines the exact process for executing tasks on the
Ratatoskr Trading Platform. Every task follows this protocol.
No steps are optional. No steps can be reordered.

---

## Setup (One Time)

### Terminal Layout
Open three terminal windows, each running Claude Code from a different directory:

```bash
# Terminal 1 — BUILDER
cd /path/to/trading-platform/studio/AGENTS/builder
claude

# Terminal 2 — VALIDATOR
cd /path/to/trading-platform/studio/AGENTS/validator
claude

# Terminal 3 — LIBRARIAN
cd /path/to/trading-platform/studio/AGENTS/librarian
claude
```

Each terminal automatically loads:
1. Its own CLAUDE.md (agent-specific instructions)
2. The root CLAUDE.md (shared rules + @imported canonical state files)

### Verify Setup
In each terminal, ask: "What is your role and what files have you loaded?"
Each agent should correctly identify itself and confirm it has read the
project state files.

---

## Task Execution Loop

Every task follows these four phases. A task is NOT complete until
all four phases finish successfully.

```
Phase 1: EXECUTE  →  Phase 2: VALIDATE  →  Phase 3: UPDATE  →  Phase 4: CONFIRM
(Builder)            (Validator)             (Librarian)          (You)
```

---

### Phase 1 — EXECUTE (Builder Terminal)

**You say:**
```
Execute TASK-{ID}. The task packet is at
/studio/TASKS/TASK-{ID}-{name}/TASK.md
```

**The Builder will:**
1. Check STATUS_BOARD.yaml — verify task is "ready" (not blocked)
2. Read the task packet
3. Read all files listed in the "Read First" section
4. Confirm its understanding of scope
5. Execute the task
6. Create BUILDER_OUTPUT.md in the task directory

**You verify before moving on:**
- [ ] BUILDER_OUTPUT.md exists at /studio/TASKS/TASK-{ID}-{name}/BUILDER_OUTPUT.md
- [ ] Every section of the template is filled in (no missing sections)
- [ ] The Builder has stated its assumptions and ambiguities

**If the Builder asks you a question:**
You can answer directional questions ("should I use approach A or B?").
Do NOT answer engineering-detail questions — those should be in the specs.
If the specs don't cover it, that's a gap to fix before proceeding.

**Gate: Do NOT proceed to Phase 2 until BUILDER_OUTPUT.md exists and is complete.**

---

### Phase 2 — VALIDATE (Validator Terminal)

**You say:**
```
Validate TASK-{ID}. The task directory is at
/studio/TASKS/TASK-{ID}-{name}/
```

**The Validator will:**
1. Read the task packet (TASK.md)
2. Read the builder output (BUILDER_OUTPUT.md)
3. Read all referenced specs and canonical files
4. INDEPENDENTLY inspect the actual repo files
5. Fill in the complete validation checklist
6. Create VALIDATION.md with a final RESULT: PASS or FAIL

**If RESULT: FAIL**
1. Read the Validator's "Required Fixes" section
2. Go back to the Builder terminal
3. Say: "TASK-{ID} failed validation. Here are the required fixes: [paste fixes]"
4. The Builder fixes the issues and updates BUILDER_OUTPUT.md
5. Return to the Validator: "Re-validate TASK-{ID}"
6. Repeat until PASS

**If RESULT: PASS**
Proceed to Phase 3.

**Gate: Do NOT proceed to Phase 3 until VALIDATION.md exists and says RESULT: PASS.**

---

### Phase 3 — UPDATE (Librarian Terminal)

**You say:**
```
TASK-{ID} has been completed and validated. Update the project state.
Task directory: /studio/TASKS/TASK-{ID}-{name}/
```

**The Librarian will:**
1. Verify VALIDATION.md says RESULT: PASS
2. Read BUILDER_OUTPUT.md and VALIDATION.md
3. Go through the update checklist for each canonical file
4. Update files in /studio/STUDIO/
5. Create LIBRARIAN_REPORT.md in the task directory

**You verify before moving on:**
- [ ] LIBRARIAN_REPORT.md exists
- [ ] STATUS_BOARD.yaml shows the task as "complete"
- [ ] The next task's dependencies are resolved (status changed from "blocked" to "ready")
- [ ] CHANGELOG.md has a new entry

**Gate: Do NOT start the next task until LIBRARIAN_REPORT.md exists and canonical files are updated.**

---

### Phase 4 — CONFIRM (You)

Quick sanity check before starting the next task:

1. Open /studio/STUDIO/STATUS_BOARD.yaml
2. Confirm the completed task shows "complete"
3. Identify the next task with status "ready"
4. Confirm its dependencies are all "complete"

If everything checks out, go back to Phase 1 with the next task.

---

## Task Directory Structure

Each task lives in its own directory with a standard set of files:

```
/studio/TASKS/TASK-{ID}-{name}/
    TASK.md              ← Task packet (created during planning, read-only during execution)
    BUILDER_OUTPUT.md    ← Builder creates this (Phase 1)
    VALIDATION.md        ← Validator creates this (Phase 2)
    LIBRARIAN_REPORT.md  ← Librarian creates this (Phase 3)
```

These four files tell the complete story of every task:
what was asked, what was done, whether it passed, and what state changed.

---

## Rules

### Task Ordering
- ALWAYS check STATUS_BOARD.yaml before starting a task
- NEVER start a task whose dependencies aren't "complete"
- NEVER run two tasks simultaneously through different builder sessions

### Agent Boundaries
- The Builder NEVER updates canonical state files
- The Validator NEVER writes code or fixes issues
- The Librarian NEVER updates files without a Validator PASS
- YOU never skip validation because it "looks fine"

### When Things Go Wrong

**Builder can't complete the task:**
Ask the Builder to document what's blocking it in BUILDER_OUTPUT.md
(even an incomplete output is useful). Bring the blocker to this
planning conversation for resolution before retrying.

**Validator finds spec gaps:**
If validation fails because the spec didn't cover something (not because
the Builder did something wrong), bring the gap to this planning
conversation. We'll update the spec, then re-run the task.

**Librarian finds inconsistencies:**
If the Librarian notices that canonical files are internally inconsistent,
it should flag this in LIBRARIAN_REPORT.md and NOT make the conflicting
update. Bring the inconsistency to this planning conversation for resolution.

**You're unsure about something:**
Come back to this planning conversation. That's what it's for.
Better to pause and clarify than to push forward with uncertainty.

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│                    TASK LOOP                             │
│                                                         │
│  1. BUILDER terminal:                                   │
│     "Execute TASK-{ID}"                                 │
│     → wait for BUILDER_OUTPUT.md                        │
│                                                         │
│  2. VALIDATOR terminal:                                 │
│     "Validate TASK-{ID}"                                │
│     → if FAIL: fix with Builder, re-validate            │
│     → if PASS: proceed                                  │
│                                                         │
│  3. LIBRARIAN terminal:                                 │
│     "Update state for TASK-{ID}"                        │
│     → wait for LIBRARIAN_REPORT.md                      │
│                                                         │
│  4. YOU: check STATUS_BOARD, start next task             │
│                                                         │
│  ⚠ NEVER skip steps. NEVER reorder steps.               │
└─────────────────────────────────────────────────────────┘
```
