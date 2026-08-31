# Phase 8b QA Report — Loop Continuation and Circuit Breaker Scenarios (Re-test)

**Branch:** main
**Scope:** `tests/stub/scenario-phase-boundary.json`, `scenario-cross-phase.json`,
`scenario-debugger-limit.json`, `scenario-phase-limit.json`, and their test functions
in `tests/test_phase8b.py` — per `myplan.md` Phase 8b. Re-verifies the fix recorded in
`docs/debug/phase-8b-debug-report.md` for the High defect from the prior QA report
(`docs/qa/phase-8b-qa-report.md` history: initial run FAIL, 1 High defect on AC 2).

---

## Tests performed

1. `python3 tests/test_phase8b.py` (fresh run, isolated temp directory) — all 4 Phase
   8b test functions report PASS; script exits 0.
2. Confirmed AC 2's subprocess exit code directly: `Exit: 0` printed for the
   cross-phase scenario, and `test_cross_phase` now asserts
   `result.returncode == 0` (added by Debugger), so a regression would fail the run,
   not just print.
3. Full existing unit test suite: `python3 -m unittest tests.test_phase3 tests.test_state tests.test_routing tests.test_phase8 -v` — 49 tests, 49 pass. No regressions.
4. `python3 tests/test_phase8.py` — all Phase 8a checks still pass (ai-run-phase
   completion, runner-override merge, `AI_ROLE_DRYRUN` baselines). No regressions.
5. Verified the real repository `project-state.md` is untouched by the test run
   (tests operate on an isolated temp directory `.ai-run-state.json`/`project-state.md`
   copy, cleaned up after each scenario) — `git status --short project-state.md`
   reports no changes.
6. Read the Debugger's change to `run_command` (`airun/__main__.py`) to confirm the
   fix is scoped to the idle-completion check described in the debug report and does
   not alter behavior for the other stop paths (human intervention, circuit-breaker
   limits) exercised by AC 3 and AC 4.

## Acceptance criteria results

| AC | Description | Result |
|---|---|---|
| 1 | `ai-run-phase` exits 0 on phase change, no runner launched in new phase, `total_runs == 3` | **PASS** |
| 2 | `ai-run` exits 0 across a phase boundary; second phase's first Implementer resolves to `implementer`; counters/`total_runs` reset at the boundary | **PASS** — exit code now 0 (was 2), counter reset and role-tiering confirmed correct, `test_cross_phase` now asserts the exit code |
| 3 | 5 Debugger requests → 1 `debugger`, 3 `senior_debugger`, stop on 5th with exit 2 and rule `§8` | **PASS** |
| 4 | 15 executions in one phase, stop before 16th with exit 2 and rule `§20` | **PASS** |

**4 of 4 acceptance criteria met.**

## Defects found

None. The High defect from the initial QA report (AC 2 exit code 2 instead of 0) is
resolved: `run_command` now re-reads `project-state.md` after each successful
iteration and returns 0 on idle completion, matching `run_phase_command`'s existing
behavior. The previously-noted test coverage gap is also closed —
`test_cross_phase` asserts `result.returncode == 0`.

## Overall outcome

**PASS**

All 4 Phase 8b acceptance criteria are met. No Critical or High defects. No
regressions in the existing 49-test suite or Phase 8a checks.
