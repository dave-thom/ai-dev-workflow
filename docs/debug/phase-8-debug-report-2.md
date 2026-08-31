# Phase 8 Debug Report (Re-fix) — Test Harness Defects

**Branch:** main
**Based on:** `docs/qa/phase-8-qa-report-2.md`

---

## Issues Investigated

Four defects from the QA re-test report, plus one additional issue discovered during debugging.

---

## Defect 1 (Critical): ModuleNotFoundError in `test_runner_override()`

**Root cause:** `tests/test_phase8.py::test_runner_override()` does `from airun.config import load_config` (line 221) without adding the project root to `sys.path`. When invoked as `python3 tests/test_phase8.py`, `sys.path[0]` is `tests/` and the `airun` package at the project root is not found.

**Files modified:** `tests/test_phase8.py`

**Corrective action:** Added `sys.path.insert(0, str(Path(__file__).parent.parent))` at line 11, after imports and before any function definitions.

---

## Defect 2 (Critical): Missing `.gitignore` file causing ignore guard failure

**Root cause:** `setup_test_directory()` at lines 116–119 assigns `gitignore_content` but never writes it to disk. The `.gitignore` file is never created, so `check_ignore_guard()` cannot verify that `.ai-run-state.json` and `.ai-run.log` are git-ignored.

**Files modified:** `tests/test_phase8.py`

**Corrective action:** Added `(Path(test_dir) / ".gitignore").write_text(gitignore_content)` after the `gitignore_content` assignment. Also added `.ai-run.json` to the ignore list (see additional defect below).

---

## Defect 3 (Critical): Stub scenario unrunnable due to git handoff guard

**Root cause:** `tests/stub/stub-runner.py` only edits `project-state.md` and writes `.stub-step` — it never commits or pushes. The orchestrator's `check_git_handoff_guard()` requires a clean, pushed tree before launching Tester. Every Tester transition in `scenario-implementer-to-git.json` (steps 1 and 3) hits this guard because the previous runner's edits remain uncommitted.

**Files modified:** `tests/stub/stub-runner.py`

**Corrective action:** Added `_git_commit_and_push()` function that performs `git add project-state.md .stub-step`, `git commit`, and `git push` after each stub runner invocation. Added `import subprocess` to support the git operations.

---

## Defect 4 (High): `git init` without `-b main` causes branch mismatch

**Root cause:** `setup_test_directory()` at line 121 runs `git init` without `-b main` / `--initial-branch=main`. On machines without `init.defaultBranch=main` configured globally (the default on Git 2.55.0), this creates a `master` branch. `check_git_handoff_guard()` then fails with `Current branch 'master' does not match expected 'main'` because the fixture's `project-state.md` hard-codes `Branch: main`.

**Files modified:** `tests/test_phase8.py`

**Corrective action:** Changed `["git", "init"]` to `["git", "init", "-b", "main"]`.

---

## Additional Defect: `.ai-run.json` not ignored, dirtying the working tree

**Root cause:** `test_ai_run_phase()` writes a project-local `.ai-run.json` config file after `setup_test_directory()` returns and the git repo is established. This file is never committed or git-ignored, so `git status --porcelain` shows `?? .ai-run.json`, failing the git handoff guard on the first Tester transition.

**Files modified:** `tests/test_phase8.py`

**Corrective action:** Added `.ai-run.json` to the `gitignore_content` string in `setup_test_directory()`.

---

## Verification Results

- 49 existing unit tests (`test_phase3`, `test_state`, `test_routing`): all pass, no regressions
- `python3 tests/test_phase8.py`: all 3 tests pass, exit 0
  - `test_ai_run_phase()`: 6-step scenario completes, exit 0, phase advances to Phase 9
  - `test_runner_override()`: config merge works correctly
  - `test_ai_role_dryrun()`: all dry-run tests pass
- Runner sequence confirmed: `implementer, tester, debugger, tester, reviewer, git`

---

## Known Issues

- AC2–AC8 still lack test coverage (scenarios and test functions) — not within Debugger scope
- `test_ai_run_phase()` only covers AC1 (6-step scenario); other acceptance criteria require additional scenario files and test functions