# Phase 11 Review — Contradictory State Validation (§22)

**Branch:** `phase/phase-11`
**Commits under review:** `02e3610` (Contradictory State Validation), `0416990`
(fix: `pinned_phase` parameter), `f03ed4c` (debug report, project-state update)
**Inputs:** `docs/qa/phase-11-qa-report.md` (PASS, re-test),
`docs/debug/phase-11-debug-report.md`, `myplan.md` Phase 11 acceptance criteria 1–6.

---

## Verification performed

Independently re-ran, rather than relying solely on the QA report:

1. `git status --porcelain -- airun/ bin/ config/ tests/` confirms the working
   tree exactly matches `HEAD` (`f03ed4c`) except pre-existing, out-of-scope
   Phase 10 untracked artifacts (`tests/test_phase10.py`,
   `tests/stub/scenario-phase10-midphase-edit.json`, `airun/__pycache__/`).
2. `python3 tests/test_phase11.py` — all 7 checks (AC1–AC6, including the AC6
   sub-runs) pass at the committed revision.
3. Read `airun/invariants.py` in full: four rules (R1–R4), each a direct,
   readable translation of the plan's §22 wording, evaluated only on
   post-execution state and only for the role the orchestrator itself
   launched.
4. Read the `check_invariants` call site in `airun/__main__.py:229–247`:
   correctly placed after the `done` log line and before the phase-advance
   guardrail and progress check, so a violation is logged and stops with
   exit 2 and rule `§22` before any other post-execution check can mask it.
5. Read `airun/runtime.py`'s `load()` fix: `pinned_phase` is optional,
   defaults to `None`, and `effective_phase` falls back to `current_phase`
   when absent — a minimal, mechanical change matching the debug report's
   description, with no behavioural change to callers that don't pass it.
6. Read all five new scenario files (`scenario-phase11-r1..r4`,
   `r4-disabled`) — each exercises a genuine contradiction (or, for the
   disabled case, a genuine non-contradiction with the same field changes),
   matching the plan's AC1–AC4 wording exactly.
7. Confirmed commit `02e3610`'s diff stays within the plan's declared Phase
   11 scope (`airun/invariants.py`, `airun/__main__.py`, stub scenarios/
   runner, `tests/test_phase11.py`); no role-prompt changes.

## Acceptance criteria

All 6 Phase 11 acceptance criteria are met, confirmed independently:

| AC | Result |
|---|---|
| 1 — R1 (untested handoff to Implementer tier) stops exit 2, §22 | PASS |
| 2 — R2 (Reviewer handoff, QA not pass) stops exit 2, §22 | PASS |
| 3 — R3 (Git Assistant handoff, Review not approved) stops exit 2, §22 | PASS |
| 4 — R4 (non-Git phase change) stops exit 2, §22; disabled via `limits` it doesn't | PASS |
| 5 — Full normal path (`scenario-implementer-to-git.json`) exits 0, `total_runs == 6` | PASS |
| 6 — Phase 8b/8c scenarios pass unchanged | PASS |

## Defect 1 (Critical, prior QA FAIL) — resolution confirmed

The missing `pinned_phase` parameter on `RuntimeState.load` (root cause:
Phase 10 scope spill — the caller was updated, the callee wasn't) is fixed
correctly: the parameter is optional and additive, `effective_phase` replaces
`current_phase` consistently through both the initial default-construction
path and the phase-reconciliation path, and no caller that omits the
argument changes behaviour. `tests/test_phase8b.py`, `tests/test_phase8c.py`
and `tests/test_phase9.py` all pass unchanged, confirming no regression from
this fix.

## Findings

### Low — `IMPLEMENTER_TIERS` includes an unreachable value

**Location:** `airun/invariants.py:11`

`IMPLEMENTER_TIERS = {"implementer", "senior_implementer"}` is used to test
`new_state.next_role` (R1). The `Next Role` field in `project-state.md` is
always written by a role as a logical role name (`Implementer`), never as a
resolved runner tier (`senior_implementer` is an internal `routing.py`
concept and is never written back to `project-state.md`). The
`senior_implementer` branch is therefore dead in this context. Harmless —
defensive, not incorrect — but slightly misleading about where tier
resolution happens.

**Recommendation:** narrow to `{"implementer"}` or add a one-line comment
noting the set is defensive against a hypothetical future writer. Not
blocking.

## Architectural / scope compliance

Changes are confined to the declared Phase 11 scope plus the targeted
`runtime.py` defect fix, which the debug report correctly traces to a
Phase 10/11 boundary scope spill rather than new work. No speculative
changes, no role-prompt edits, no scope creep. The four rules match the
plan's §22 wording precisely and are conservative (evaluated only on
orchestrator-launched transitions), matching the plan's stated intent to
avoid false stops under manual operation.

## Decision

**APPROVE**

0 Critical, 0 High, 0 Medium, 1 Low (non-blocking, cosmetic). All 6
acceptance criteria are met at the committed revision, the prior Critical
defect is resolved and verified independently, and no regressions were found
across the Phase 11, 8b, 8c and 9 suites.
