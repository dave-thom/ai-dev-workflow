# Phase 8 Debug Report

**Source:** docs/qa/phase-8-qa-report.md

---

## Defect 1 — `setup_test_directory()` missing return (Critical)

**Root cause:** `tests/test_phase8.py:setup_test_directory()` computed `test_dir` and `ai_platform` but never returned them. The caller `test_ai_run_phase()` unpacked via `test_dir, ai_platform = setup_test_directory()`, which raised `TypeError: cannot unpack non-iterable NoneType object`.

**Fix:** Added `return test_dir, ai_platform` at end of `setup_test_directory()` (`tests/test_phase8.py:133`).

---

## Defect 2 — Stub runner never advances steps (Critical)

**Root cause:** `tests/stub/stub-runner.py` read `STUB_STEP` only from the environment variable, which is inherited from the orchestrator process at `STUB_STEP=0` on every invocation. No persistence mechanism existed to advance the step counter across process boundaries.

**Fix:** Added file-based step persistence via `.stub-step`:
- New helper `_read_step()` checks for `.stub-step` file first, falls back to `STUB_STEP` env var
- New helper `_write_next_step(step)` writes `step + 1` to `.stub-step` after execution
- Called `_write_next_step(step)` in `main()` before exit
- File is cleaned up by the test's `shutil.rmtree(test_dir)`

---

## Defect 3 — Scenario step 2 encodes QA failure as non-zero exit (Critical)

**Root cause:** `tests/stub/scenario-implementer-to-git.json` step 2 ("Tester fails") used `"exit_code": 1` to represent the Tester handing to Debugger. But `airun/__main__.py:next_command` (line 217) treats any non-zero child exit as a runtime failure, returning exit 3 without inspecting `Next Role`.

**Fix:** Changed step 2's `exit_code` from `1` to `0`. A QA FAIL with `Next Role: Debugger` must be represented by the stub updating `project-state.md` and exiting 0 — matching the orchestrator's existing Phase 7 semantics.

---

## Defect 4 — Repository `project-state.md` missing `Review` field (Critical)

**Root cause:** Commit `16d6b2b` deleted the `Review` field from `project-state.md`'s `## Execution` section. The tester's working-tree changes (uncommitted) re-added the field.

**Status:** Resolved in working tree. No additional action needed.

---

## Defect 5 — Runner-override fixture never exercised (High)

**Root cause:** `tests/fixtures/runner-override-project/.ai-run.json` existed but no test invoked `load_config` against it.

**Fix:** Added `test_runner_override()` to `tests/test_phase8.py` that:
- Creates a temp directory with a local `.ai-run.json`
- Calls `airun.config.load_config()` from that directory
- Asserts the reviewer role command override and `phase_max_executions` limit override are merged correctly

---

## Defect 6 — `AI_ROLE_DRYRUN=1` has zero test coverage (High)

**Root cause:** No test invoked `bin/ai-role` with `AI_ROLE_DRYRUN=1`.

**Fix:** Added `test_ai_role_dryrun()` to `tests/test_phase8.py` that:
- Runs `bin/ai-role opencode <role>` with `AI_ROLE_DRYRUN=1` for implementer, debugger, and git roles
- Verifies exit 0 and output structure (`opencode` header, `--prompt`, lifecycle + role prompt content)
- Compares against Phase 1 baseline fixtures where available

---

## Files Modified

| File | Change |
|------|--------|
| `tests/test_phase8.py` | Added `return` to `setup_test_directory()`; added `test_runner_override()` and `test_ai_role_dryrun()` |
| `tests/stub/stub-runner.py` | Added file-based step persistence via `.stub-step` |
| `tests/stub/scenario-implementer-to-git.json` | Changed step 2 `exit_code` from `1` to `0` |

## Remaining Known Issues

None.