# Phase 8b Debug Report

**QA Report:** docs/qa/phase-8b-qa-report.md
**Branch:** main

---

## Issue Investigated

AC 2 (cross-phase scenario): `ai-run` exits with code 2 instead of 0 when the
workflow reaches a normal idle completion ("no next role").

## Root Cause

`run_command` (`airun/__main__.py:325`) loops calling `next_command` and
propagates any non-zero exit code. When the workflow reaches idle state
(`next_role` becomes None/empty), `next_command` calls `resolve()` which hits
routing rule 4 (§22, "Workflow idle (no next role)"), returning a `stop`
Decision. `next_command` returns 2 for all stop decisions, and `run_command`
propagates that 2.

`run_phase_command` (`airun/__main__.py:266`) already had an idle-completion
check (lines 302–306) that re-reads `project-state.md` after each successful
step and returns 0 if `next_role` is Architect or empty. `run_command` lacked
this check entirely.

## Files Modified

| File | Change |
|---|---|
| `airun/__main__.py` | Added idle-completion check to `run_command` after each successful `next_command` call: re-reads `project-state.md`, returns 0 if `next_role` is architect, empty, or `"none"` |
| `tests/test_phase8b.py` | Added `assert result.returncode == 0` to `test_cross_phase` to verify AC 2's exit-code requirement |

## Corrective Actions

1. Inserted 7 lines in `run_command` (lines 348–354) to reload `project-state.md`
   after each successful iteration and return 0 if the workflow has reached an
   idle-completion state.
2. Extended `test_cross_phase` to assert `result.returncode == 0`, closing the
   coverage gap identified in the QA report.

## Verification

- `python3 tests/test_phase8b.py` — all 4 ACs pass, exit 0
- `python3 -m unittest tests.test_phase3 tests.test_state tests.test_routing tests.test_phase8 -v` — 49/49 pass, no regressions
- `python3 tests/test_phase8.py` — all Phase 8a checks pass

## Remaining Known Issues

None.