# Phase 11 QA Report — Contradictory State Validation (§22) — Re-test

**Branch:** `phase/phase-11`
**Commits under test:** `0416990` (fix(phase-11): add pinned_phase parameter to
RuntimeState.load), `f03ed4c` (chore(phase-11): add debug report and update
project-state for re-test)
**Scope:** `airun/invariants.py`, `airun/__main__.py`, `airun/runtime.py`, scenarios
under `tests/stub/`, `tests/test_phase11.py`, per `myplan.md` Phase 11 acceptance
criteria 1–6.

---

## Context

This is a re-test following the prior FAIL (see git history of this file). Defect
1 (Critical) — the missing `pinned_phase` parameter on `RuntimeState.load` — was
fixed and committed at `0416990`. This report validates the fix against the
committed state, not the working tree.

## Tests performed

1. Confirmed the fix is actually committed: `git show --stat 0416990` shows
   `airun/runtime.py` modified (9 insertions, 4 deletions), and `git diff --stat
   HEAD -- airun/ bin/ config/ tests/test_phase11.py` is empty — the working
   tree exactly matches `HEAD` (`f03ed4c`) for all relevant code. No uncommitted
   edit is propping up this result.
2. `git status --porcelain`: only pre-existing untracked Phase 10 artifacts
   (`tests/test_phase10.py`, `tests/stub/scenario-phase10-midphase-edit.json`,
   `airun/__pycache__/`) remain, unrelated to Phase 11 scope (noted in the prior
   report and in the Phase 11 debug report; not addressed here as out of scope).
3. `python3 tests/test_phase11.py` — all 7 checks (AC1–AC6, including the AC6
   sub-runs of `test_phase8b.py`/`test_phase8c.py`) **pass**, exit 0.
4. Full regression pass: `tests/test_phase8.py`, `tests/test_phase8b.py`,
   `tests/test_phase8c.py`, `tests/test_phase9.py` — all **pass**, exit 0.
5. `tests/test_phase3.py`, `tests/test_state.py`, `tests/test_routing.py` — all
   **pass** with `PYTHONPATH=.` (pre-existing environment quirk noted in the
   prior report; unrelated to Phase 11).

## Acceptance criteria results

| AC | Description | Result (committed `f03ed4c`) |
|---|---|---|
| 1 | R1 scenario (Implementer hands back to Implementer with QA untested) stops exit 2, rule §22 | PASS |
| 2 | R2 scenario (hand to Reviewer, QA=FAIL) stops exit 2, rule §22 | PASS |
| 3 | R3 scenario (hand to Git Assistant without approval) stops exit 2, rule §22 | PASS |
| 4 | R4 scenario stops exit 2 with role change; disabled via `limits` it does not | PASS |
| 5 | `scenario-implementer-to-git.json` full normal path exits 0, `total_runs == 6` | PASS |
| 6 | Phase 8b and 8c scenarios continue to pass unchanged | PASS |

**6 of 6 acceptance criteria met at the committed revision.**

## Defects found

None. Defect 1 (Critical, prior report) is resolved: `RuntimeState.load` now
accepts `pinned_phase` and reconciles via `effective_phase`, matching its caller
in `airun/__main__.py`.

## Overall outcome

**PASS**

0 Critical, 0 High, 0 Medium, 0 Low. All 6 acceptance criteria pass at the
committed revision (`f03ed4c`), verified independently of the working tree.
