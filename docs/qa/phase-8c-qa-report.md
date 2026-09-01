# Phase 8c QA Report — Stop Condition Scenarios

**Branch:** feature/phase-8c
**Scope:** `tests/stub/scenario-architect-stop.json`, `scenario-human-intervention-stop.json`,
`scenario-runner-failure.json`, `tests/test_phase8c.py`, and `airun/__main__.py`
(Debugger fix for Defect 1), per `myplan.md` Phase 8c acceptance criteria 1–4.

This is a re-test following the Debugger's fix for Defect 1
(`docs/debug/phase-8c-debug-report.md`, commit `44d840d`). Previous QA pass:
`git show 465baa9:docs/qa/phase-8c-qa-report.md`.

---

## Tests performed

1. `python3 tests/test_phase8c.py` (fresh run, isolated temp directories) — all three
   test functions print PASS and the script exits 0. `test_architect_stop` now asserts
   `returncode == 2` and checks for `§12` in the output (corrected per the debug
   report's test-authoring note in the prior QA pass).
2. Full regression suite: `PYTHONPATH=$(pwd) python3 tests/test_state.py` (10 tests),
   `tests/test_routing.py` (24 tests), `tests/test_phase3.py` (15 tests), plus
   `tests/test_phase8.py` and `tests/test_phase8b.py` (all pass). No regressions.
3. Confirmed scope by diffing this phase's commits against the prior phase boundary
   (`git diff --stat 62ca8d9 HEAD`): only the Phase 8c scenario/test files, the
   Defect 1 fix in `airun/__main__.py`, the debug report, and `project-state.md`
   changed. No files outside the Debugger's authorized scope were touched.
4. Manually reproduced the Architect-stop scenario **twice**, independently of
   `test_phase8c.py`'s own assertions, in isolated temp git repos + bare remotes with
   `.ai-run.json` pointed at the stub runner, invoking `bin/ai-run-phase` and
   `bin/ai-run` directly via `STUB_SCENARIO`/`STUB_STEP` env vars against
   `scenario-architect-stop.json` from a fresh `Next Role: Implementer` state, and
   capturing the real exit code and stdout/stderr:
   - `bin/ai-run-phase`: prints `Launching implementer -> implementer...` then
     `Stop: Architect must never be launched (§12)`, exits **2**.
   - `bin/ai-run`: prints `Launching implementer -> implementer...` then
     `Stop: Architect must never be launched (§12)`, exits **2**.
   Neither command printed "Workflow completed" or exited 0, and neither launched a
   runner beyond the single Implementer step.
5. Read the fix in `airun/__main__.py`: both `run_phase_command` (line ~304) and
   `run_command` (line ~351) now only short-circuit on empty/`"none"` `Next Role`
   (genuine idle completion); the `"architect"` case was removed from both, so an
   `Architect` handoff falls through to the next `next_command()` iteration, where
   `resolve()` classifies it `action="stop"`, `rule="§12"` and returns exit 2.

## Acceptance criteria results

| AC | Description | Result |
|---|---|---|
| 1 | `Next Role: Architect` stops both `ai-run-phase` and `ai-run` with exit 2 and rule `§12`, launches no further runner | **PASS** |
| 2 | `Human Intervention Required: Yes` stops both commands with exit 2 and rule `§13`, launches no further runner | PASS |
| 3 | Non-zero runner exit stops both commands with exit 3, reporting phase/role/runner/exit status, no retry | PASS |
| 4 | The executed step's counter is recorded in `.ai-run-state.json` in all three scenarios | PASS |

**4 of 4 acceptance criteria met.**

## Defects found

None. Defect 1 (Architect stop returning exit 0/"Workflow completed" instead of
exit 2/§12) is resolved and independently confirmed via manual reproduction outside
the test harness, matching the reproduction method used to originally surface the
defect.

## Overall outcome

**PASS**

0 Critical, 0 High, 0 Medium, 0 Low defects. All 4 acceptance criteria met. No
regressions in the full existing test suite (60+ tests across `test_state.py`,
`test_routing.py`, `test_phase3.py`, `test_phase8.py`, `test_phase8b.py`,
`test_phase8c.py`).
