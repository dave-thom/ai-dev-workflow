# Phase 8 QA Report (Re-test 2) — Loop Commands, Test Harness and Documentation

**Branch:** main
**Scope:** re-test of fixes recorded in `docs/debug/phase-8-debug-report-2.md`, against the same scope as `docs/qa/phase-8-qa-report.md` / `phase-8-qa-report-2.md`: `run-phase`/`run` subcommands in `airun/__main__.py`, `bin/ai-run-phase`, `bin/ai-run`, `tests/stub/`, `tests/fixtures/runner-override-project/`, README orchestrator section, per myplan.md Phase 8.

---

## Tests performed

1. Full existing unit test suite: `python3 -m unittest tests.test_phase3 tests.test_state tests.test_routing -v` — 49 tests, 49 pass. No regressions.
2. `python3 tests/test_phase8.py`, invoked exactly as documented (the same invocation that crashed in both prior QA passes) — now runs to completion, exit 0, all 3 tests pass.
3. Manual, non-cleaned-up reproduction of the fixture setup and the full 6-step `scenario-implementer-to-git.json` scenario (mirroring `setup_test_directory()` but preserving the directory afterward) to independently verify claims not directly asserted by the script's own output:
   - `.ai-run-state.json` contents after the run: `total_runs: 6`, counters `{implementer: 1, tester: 2, debugger: 1, reviewer: 1, git: 1}` — confirms the exact runner sequence `implementer, tester, debugger, tester, reviewer, git` required by AC1.
   - `project-state.md` after the run: `Active Phase: Phase 9`, and free of any orchestrator counters or execution history (only the standard Workflow/Git/Execution/Deliverables/Escalation fields).
   - `git log` in the fixture: 6 stub commits (`stub: step 0`..`stub: step 5`) on top of `init`, `git status --porcelain` empty, confirming the stub-runner's commit+push fix satisfies the git handoff guard at every Tester transition.
4. Confirmed no test file or scenario fixture exists for AC2–AC8 (`grep -n "def test_" tests/test_phase8.py`; `ls tests/stub/*.json` shows only `scenario-implementer-to-git.json`) — unchanged from both prior QA reports.
5. Reviewed `README.md` orchestrator section — unchanged, still satisfies AC12.

## Defects from `docs/debug/phase-8-debug-report-2.md` — verification

| # | Defect | Status |
|---|---|---|
| 1 (Critical) | `ModuleNotFoundError` in `test_runner_override()` | **Fixed** — `sys.path.insert` added at `tests/test_phase8.py:11`; script now imports `airun.config` correctly under the documented `python3 tests/test_phase8.py` invocation |
| 2 (Critical) | `.gitignore` never written to fixture | **Fixed** — `tests/test_phase8.py` now writes the file before `git init`; ignore guard passes |
| 3 (Critical) | Stub scenario unrunnable under git handoff guard | **Fixed** — `tests/stub/stub-runner.py` now commits and pushes after every step; verified 6 commits land on `origin/main` with a clean working tree throughout |
| 4 (High) | `git init` without `-b main` | **Fixed** — `tests/test_phase8.py` now runs `git init -b main`; verified the branch is `main` regardless of `init.defaultBranch` |
| Additional | `.ai-run.json` not git-ignored | **Fixed** — added to `gitignore_content` |

All five fixes are confirmed correct. No regressions introduced (49/49 existing tests still pass).

## Acceptance criteria results

| AC | Description | Result |
|---|---|---|
| 1 | 6-step scenario completes under `ai-run-phase`, exit 0, `total_runs==6`, correct runner sequence | **PASS** — verified directly (see Tests performed §3) |
| 2 | `ai-run-phase` exits 0 without starting next phase when Active Phase changes | **FAIL** — no test exists |
| 3 | Two-phase `ai-run` scenario resets counters correctly | **FAIL** — no test exists |
| 4 | Four Debugger requests stop at third `senior_debugger`, exit 2 | **FAIL** — no test exists |
| 5 | 15-execution scenario stops before 16th, exit 2 | **FAIL** — no test exists |
| 6 | `Next Role: Architect` stops both loops, exit 2 | **FAIL** — no test exists |
| 7 | `Human Intervention Required: Yes` stops both loops, exit 2 | **FAIL** — no test exists |
| 8 | Non-zero runner exit stops both loops, exit 3, no retry | **FAIL** — no test exists |
| 9 | Manual alias invocation still works via `AI_ROLE_DRYRUN=1` | **PASS** — all 3 cases pass, `o-dev` and `o-debug` match baselines exactly |
| 10 | Project-local `.ai-run.json` reassigns a runner, tested guarantee | **PASS** — `test_runner_override()` runs and passes under the documented invocation |
| 11 | `project-state.md` free of orchestrator counters/history after harness runs | **PASS** — verified directly (see Tests performed §3) |
| 12 | README documents commands, config, runtime files, stop exit codes, runner reassignment | **PASS** — unchanged, all elements present |

**5 of 12 acceptance criteria met** — up from 1 of 12. The debug-report-2 fixes are confirmed correct and resolve AC1, AC9, AC10, and AC11 (all previously blocked by the same class of harness-crash defects). AC2–AC8 remain entirely without test coverage.

## Defects found

### High — AC2–AC8 (7 of 12 acceptance criteria) have zero test coverage

No scenario fixture other than `scenario-implementer-to-git.json` exists in `tests/stub/`, and `tests/test_phase8.py` defines no test function exercising the phase-boundary stop (AC2), the two-phase counter-reset path (AC3), the senior-debugger circuit breaker (AC4), the phase-execution circuit breaker (AC5), the Architect stop (AC6), the Human Intervention stop (AC7), or the non-zero-exit/no-retry stop (AC8). These are unchanged from the original QA report (`docs/qa/phase-8-qa-report.md`) and the first re-test (`docs/qa/phase-8-qa-report-2.md`) — no work has been done against this gap across two Debugger passes.

`docs/debug/phase-8-debug-report-2.md`'s "Known Issues" section explicitly states this gap is "not within Debugger scope." Debugger has now twice fixed defects in the existing harness/scenario without adding the missing scenarios or test functions. Continuing to route this back to Debugger under the current defect-fix framing is unlikely to close the gap: building 6 new scenario fixtures plus corresponding test functions is new deliverable work (part of Phase 8's original scope — "an offline stub harness proving the full-phase and cross-phase paths"), not a bug fix in existing code.

**Failure scenario:** none of AC2–AC8's described behaviors (phase-boundary stop, counter reset, both circuit breakers, both hard-stop conditions, no-retry-on-runtime-failure) have ever been exercised by an automated test. Regressions in any of this routing/stop logic would go undetected.

## Overall outcome

**FAIL**

1 High defect (carried forward, unchanged in substance across three QA passes). 7 of 12 acceptance criteria remain unmet, all for the same reason: no test exists. The four defects targeted by this debug round (plus one additional) are all confirmed fixed and account for the improvement from 1/12 to 5/12 — that work should not be repeated. What remains is missing test coverage that the Debugger has stated is outside its remit, which is a scope/ownership question this report escalates rather than routes back into another identical Debugger cycle.
