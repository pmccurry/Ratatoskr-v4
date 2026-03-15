# Validation Report — TASK-{ID}

## Task
(paste the task title here)

## Pre-Flight Checks
- [ ] Task packet read completely
- [ ] Builder output read completely
- [ ] All referenced specs read
- [ ] DECISIONS.md read
- [ ] GLOSSARY.md read
- [ ] cross_cutting_specs.md read
- [ ] Repo files independently inspected (not just builder summary)

---

## 1. Builder Output Quality

### Is BUILDER_OUTPUT.md complete?
- [ ] Completion Checklist present and filled
- [ ] Files Created section present and non-empty
- [ ] Files Modified section present
- [ ] Files Deleted section present
- [ ] Acceptance Criteria Status — every criterion listed and marked
- [ ] Assumptions section present (explicit "None" is acceptable)
- [ ] Ambiguities section present (explicit "None" is acceptable)
- [ ] Dependencies section present
- [ ] Tests section present
- [ ] Risks section present
- [ ] Deferred Items section present
- [ ] Recommended Next Task section present

Section Result: ✅ PASS / ❌ FAIL
Issues: (list any, or "None")

---

## 2. Acceptance Criteria Verification

(copy EVERY criterion from the task packet, verify independently)

| # | Criterion | Builder Claims | Validator Verified | Status |
|---|-----------|---------------|-------------------|--------|
| 1 | (text)    | ✅/❌          | ✅/❌ (evidence)    | PASS/FAIL |
| 2 | (text)    | ✅/❌          | ✅/❌ (evidence)    | PASS/FAIL |
(continue for ALL criteria)

Section Result: ✅ PASS / ❌ FAIL
Issues: (list any, or "None")

---

## 3. Scope Check

- [ ] No files created outside task deliverables
- [ ] No files modified outside task scope
- [ ] No modules added that aren't in the approved list (auth, market_data, strategies, signals, risk, paper_trading, portfolio, observability, common)
- [ ] No architectural changes or new patterns introduced
- [ ] No live trading logic present
- [ ] No dependencies added beyond what the task requires

Section Result: ✅ PASS / ❌ FAIL
Issues: (list any, or "None")

---

## 4. Naming Compliance

- [ ] Python files use snake_case
- [ ] TypeScript component files use PascalCase
- [ ] TypeScript utility files use camelCase
- [ ] Folder names match module specs exactly
- [ ] Entity names match GLOSSARY exactly
- [ ] Database-related names follow conventions (_id, _at, _json suffixes)
- [ ] No typos in module or entity names

Section Result: ✅ PASS / ❌ FAIL
Issues: (list any, or "None")

---

## 5. Decision Compliance

- [ ] No live trading logic (DECISION-002)
- [ ] Tech stack matches approved stack — Python 3.12, FastAPI, React, Vite, TypeScript, PostgreSQL (DECISIONS 007-009)
- [ ] No Redis, microservices, or event bus (architecture constraints)
- [ ] No off-scope modules (DECISION-001)
- [ ] Python tooling uses uv (DECISION-010)
- [ ] API is REST-first (DECISION-011)

Section Result: ✅ PASS / ❌ FAIL
Issues: (list any, or "None")

---

## 6. Structure and Convention Compliance

- [ ] Folder structure matches cross_cutting_specs and relevant module spec
- [ ] File organization follows the defined module layout
- [ ] Empty directories have .gitkeep files
- [ ] __init__.py files exist where required
- [ ] No unexpected files in any directory

Section Result: ✅ PASS / ❌ FAIL
Issues: (list any, or "None")

---

## 7. Independent File Verification

### Files builder claims to have created that ACTUALLY EXIST:
(list verified files — spot check at minimum, full check for scaffold tasks)

### Files that EXIST but builder DID NOT MENTION:
(list any unexpected files found — these may indicate scope creep)

### Files builder claims to have created that DO NOT EXIST:
(list any missing files — these indicate builder hallucination)

Section Result: ✅ PASS / ❌ FAIL
Issues: (list any, or "None")

---

## Issues Summary

### Blockers (must fix before PASS)
(list all, or "None")

### Major (should fix before proceeding)
(list all, or "None")

### Minor (note for future, does not block)
(list all, or "None")

---

## Risk Notes
(things that aren't wrong but could cause problems for future tasks)

---

## RESULT: PASS / FAIL

(if FAIL: list the specific fixes required before re-validation)
(if PASS: confirm the task is ready for Librarian update)
