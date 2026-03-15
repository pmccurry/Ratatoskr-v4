# Librarian Update Checklist — TASK-{ID}

## Pre-Flight
- [ ] VALIDATION.md exists and shows RESULT: PASS
- [ ] BUILDER_OUTPUT.md read
- [ ] All current canonical files read

---

## STATUS_BOARD.yaml
- [ ] Completed task marked as "complete" with completed_at date
- [ ] All dependent tasks checked — any now unblocked changed to "ready"
- [ ] New tasks added if builder discovered them
- [ ] No other task statuses changed without reason

Changes made: (describe, or "No changes needed")

---

## PROJECT_STATE.md
- [ ] Current Milestone updated (if milestone changed)
- [ ] Current Phase updated (if phase changed)
- [ ] New constraints added (if any discovered)
- [ ] "Last Updated" date changed to today
- [ ] No sections modified that this task didn't affect

Changes made: (describe, or "No changes needed — only date updated")

---

## DECISIONS.md
- [ ] New decisions added ONLY if explicitly confirmed by builder/validator
- [ ] Decision IDs are sequential (next number after the last existing)
- [ ] No speculative or suggested decisions added
- [ ] Existing decisions not modified

Changes made: (describe, or "No new decisions")

---

## ROADMAP.md
- [ ] Milestone marked complete if all its tasks are done
- [ ] "Current Milestone" pointer updated if milestone changed
- [ ] New tasks noted under appropriate milestone if discovered
- [ ] No structural changes to the roadmap

Changes made: (describe, or "No changes needed")

---

## GLOSSARY.md
- [ ] New terms added if builder introduced new domain concepts
- [ ] Existing terms not modified
- [ ] Same format as existing entries

Changes made: (describe, or "No new terms — glossary unchanged")

---

## CHANGELOG.md
- [ ] New entry appended (NEVER edit previous entries)
- [ ] Entry includes: task ID, title, date, status, summary, file counts, notes
- [ ] Summary is 1-3 factual sentences

Entry added: (paste the entry)

---

## Files Updated Summary

| File | Changed? | What Changed |
|------|----------|-------------|
| STATUS_BOARD.yaml | Yes/No | (brief description) |
| PROJECT_STATE.md | Yes/No | (brief description) |
| DECISIONS.md | Yes/No | (brief description) |
| ROADMAP.md | Yes/No | (brief description) |
| GLOSSARY.md | Yes/No | (brief description) |
| CHANGELOG.md | Yes | (always — new entry appended) |

---

## Confirmation
All updates are complete. The next task in STATUS_BOARD.yaml that shows
status "ready" may now be assigned to the Builder.
