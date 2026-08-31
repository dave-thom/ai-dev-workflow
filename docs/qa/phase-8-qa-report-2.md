# Phase 8 QA Report (Re-test) — Loop Commands, Test Harness and Documentation

**Branch:** main
**Scope:** re-test of fixes recorded in `docs/debug/phase-8-debug-report.md`, against the same scope as `docs/qa/phase-8-qa-report.md`: `run-phase`/`run` subcommands in `airun/__main__.py`, `bin/ai-run-phase`, `bin/ai-run`, `tests/stub/`, `tests/fixtures/runner-override-project/`, README orchestrator section, per myplan.md Phase 8.

---

## Tests performed

1. Full existing unit test suite: `python3 -m unittest tests.test_phase3 tests.test_state tests.test_routing -v` — 49 tests, 49 pass. Confirms Defect 4 (missing `Review` field) is resolved; `test_parses_current_project_state` no longer errors.
2. `python3 tests/test_phase8.py` (the deliverable's own Phase 8 acceptance script, invoked exactly as documented in the prior QA report) — still fails. See Defects 1–4 below.
3. `PYTHONPATH=. python3 tests/test_phase8.py` — run to isolate defects; confirms Defect 1 (import path) is specific to the undocumented invocation requirement, and exposes Defect 2 (ignore guard) independently.
4. Manual end-to-end reproduction of the 6-step stub scenario (`tests/stub/scenario-implementer-to-git.json`) in a hand-built fixture directory, working around Defects 1–3 one at a time, to determine whether Defects 1–3 (debug report) are the only remaining blockers for AC1. They are not — see Defect 3 below, which is architectural, not a fixture bug.
5. Confirmed no test file or scenario fixture exists for AC2–AC8 (`grep -n "def test_" tests/test_phase8.py`; `grep -rl` for limit/architect/human-intervention markers across `tests/stub/*.json`) — unchanged from the original QA report.
6. Reviewed `README.md` orchestrator section — unchanged, still satisfies AC12.

## Acceptance criteria results

| AC | Description | Result |
|---|---|---|
| 1 | 6-step scenario completes under `ai-run-phase`, exit 0, `total_runs==6`, correct runner sequence | **FAIL** — harness still cannot complete (Defects 1–3) |
| 2 | `ai-run-phase` exits 0 without starting next phase when Active Phase changes | **FAIL** — no test exists |
| 3 | Two-phase `ai-run` scenario resets counters correctly | **FAIL** — no test exists |
| 4 | Four Debugger requests stop at third `senior_debugger`, exit 2 | **FAIL** — no test exists |
| 5 | 15-execution scenario stops before 16th, exit 2 | **FAIL** — no test exists |
| 6 | `Next Role: Architect` stops both loops, exit 2 | **FAIL** — no test exists |
| 7 | `Human Intervention Required: Yes` stops both loops, exit 2 | **FAIL** — no test exists |
| 8 | Non-zero runner exit stops both loops, exit 3, no retry | **FAIL** — no test exists |
| 9 | Manual alias invocation still works via `AI_ROLE_DRYRUN=1` | **FAIL** — test exists and passes in isolation, but never runs as documented: the script crashes with an unhandled exception in the preceding test (Defect 1) before reaching this test (see Defect 4) |
| 10 | Project-local `.ai-run.json` reassigns a runner, tested guarantee | **FAIL** — test exists and passes in isolation (`PYTHONPATH=. python3 tests/test_phase8.py`), but raises `ModuleNotFoundError` and aborts the whole script when run as documented (Defect 1) |
| 11 | `project-state.md` free of orchestrator counters/history after harness runs | **FAIL** — unverifiable; harness never completes a run |
| 12 | README documents commands, config, runtime files, stop exit codes, runner reassignment | **PASS** — unchanged from prior QA pass, all elements present |

**1 of 12 acceptance criteria met** — unchanged from the original QA report. The debug fixes were individually correct but did not restore the deliverable to a working state, and did not add the test coverage the original report identified as missing for AC2–8.

## Defects found

### Critical — `python3 tests/test_phase8.py`, run exactly as the acceptance script is documented to be run, still crashes before completing

`tests/test_phase8.py::test_runner_override()` (added by the debug fix for original Defect 5) does `from airun.config import load_config` (line 221) without first adding the project root to `sys.path`. `unittest`-style invocation and `PYTHONPATH=.` both mask this because they put the project root on `sys.path[0]`, but the documented invocation (`python3 tests/test_phase8.py`, used verbatim in the original QA report and unchanged by the debug fix) puts `tests/` on `sys.path[0]` instead. The `airun` package lives at the project root, one level above `tests/`, and is never found.

**Failure scenario:** `python3 tests/test_phase8.py` → `ModuleNotFoundError: No module named 'airun'` at line 221, uncaught, script exits 1. `test_ai_role_dryrun()` (AC9) is never reached — the whole script aborts partway through `main()`, the same class of failure as the original Defect 1 (harness crashes before completing), just relocated to a different line. AC9 and AC10 are therefore still functionally uncovered by the deliverable's acceptance script, despite the debug report's claim that both were resolved by adding these tests.

### Critical — `setup_test_directory()` builds `.gitignore` content but never writes the file, so the fixture repository fails the orchestrator's own ignore guard

`tests/test_phase8.py:116-119` assigns `gitignore_content = ".ai-run-state.json\n.ai-run.log\n"` but this variable is never written to disk and never referenced again — no `.gitignore` file is created in the fixture directory before `git add .` / `git commit`. `airun/guards.py:check_ignore_guard()` (invoked unconditionally at the top of every `next` call, per `airun/__main__.py:140`) then finds `.ai-run-state.json` is not git-ignored and returns a violation.

**Failure scenario:** even with the sys.path defect above worked around, `ai-run-phase` in the fixture directory prints `Ignore guard violation: .ai-run-state.json and .ai-run.log must be git-ignored` and exits 4 on its very first `ai-next` call — the scenario never launches step 0. Verified directly: `python3 tests/test_phase8.py` (test 1) shows exactly this output.

### Critical — the stub scenario cannot satisfy the git handoff guard the orchestrator enforces before launching Tester, so AC1's scenario is structurally unrunnable by the current harness

`airun/guards.py:check_git_handoff_guard()` (myplan.md §27) requires, before every launch of Tester: matching branch, `git status --porcelain` empty, an upstream configured, and local `HEAD` equal to the upstream commit. `tests/stub/stub-runner.py` only ever edits `project-state.md` (and now `.stub-step`) — it never commits or pushes. `scenario-implementer-to-git.json`'s own sequence (Implementer → Tester → Debugger → Tester → Reviewer → Git) has no committing step between the Implementer/Debugger steps and the following Tester steps, so the working tree is guaranteed dirty and unpushed at every Tester transition.

**Failure scenario:** manually reproducing the fixture setup with a `.gitignore` present and `git init -b main` (to work around Defects 1–2 above) still stops the scenario at exit 2, `Git handoff guard violation: Uncommitted changes present`, immediately after step 0 (Implementer). The scenario never reaches Tester, let alone Debugger, Reviewer, or Git. This is not a fixture typo — it is a gap between what the stub-runner does (edit only) and what the guard requires (clean, pushed tree) before every Tester launch, and it is unrelated to any of the three defects already fixed in `docs/debug/phase-8-debug-report.md`. `total_runs` never approaches 6.

### High — `setup_test_directory()`'s `git init` does not pin the initial branch name, so the fixture is environment-dependent and fails on any machine without `init.defaultBranch=main` configured globally

`project-state.md`'s `Branch: main` field is hard-coded in the fixture content, but `git init` (line 121) is called with no `-b main` / `--initial-branch=main`. On this machine, `git config --global init.defaultBranch` is unset, so `git init` creates a `master` branch, and `check_git_handoff_guard` immediately reports `Current branch 'master' does not match expected 'main'`. This is masked on any machine where the global default happens to be `main`, which makes the fixture non-portable and its prior "passing" status (if ever observed) environment-specific rather than a property of the code.

**Failure scenario:** on a stock `git` install (no global `init.defaultBranch` override — verified on this machine: `git config --global init.defaultBranch` returns nothing, `git --version` 2.55.0, which still defaults to `master`), the fixture's first Tester transition fails on branch mismatch before the uncommitted-changes issue (Defect 3 above) is even reached.

## Files reviewed but not modified

Per role scope, no implementation or test files were modified during this re-test. All defects above were confirmed by direct execution and, where useful, isolated hand-built reproduction outside the broken test script.

## Overall outcome

**FAIL**

3 Critical defects, 1 High defect, all newly surfaced by this re-test (none are regressions of the six defects already fixed in `docs/debug/phase-8-debug-report.md` — those fixes are confirmed correct and necessary, just not sufficient). 11 of 12 acceptance criteria remain unmet. The Phase 8 acceptance script still does not run to completion when invoked as documented, and the one scenario it does define cannot reach completion under the orchestrator's own git handoff guard regardless of the harness bugs, because the stub-runner never commits or pushes on behalf of a role. Acceptance criteria 2–8 remain entirely without test coverage, unchanged from the original QA report. Implementation is not ready to proceed to Reviewer; returning to Debugger.
