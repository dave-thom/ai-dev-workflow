# Phase 8 QA Report — Loop Commands, Test Harness and Documentation

**Branch:** main
**Scope:** `run-phase`/`run` subcommands in `airun/__main__.py`, `bin/ai-run-phase`, `bin/ai-run`, `tests/stub/` (scripted stub runner), `tests/fixtures/runner-override-project/`, README orchestrator section, per myplan.md Phase 8.

---

## Tests performed

1. Full existing unit test suite: `python3 -m unittest tests.test_phase3 tests.test_state tests.test_routing -v` — 49 tests. 48 pass; 1 error (`test_state.test_parses_current_project_state`) — see Defect 4.
2. `python3 tests/test_phase8.py` (the deliverable's own Phase 8 acceptance script) — crashes before running any assertion. See Defect 1.
3. Code reading of `airun/launcher.py`, `airun/__main__.py` (`next_command`, `run_phase_command`, `run_command`), `tests/stub/stub-runner.py`, `tests/stub/scenario-implementer-to-git.json`, `airun/runtime.py`, `airun/config.py`, `bin/ai-run-phase`, `bin/ai-run`, `README.md`.
4. Manual reproduction of the scenario's step-advancement mechanism by tracing how `STUB_STEP` is set and propagated across process launches.
5. Manual verification of the runner-override merge logic (`airun.config.load_config`) against `tests/fixtures/runner-override-project/.ai-run.json` — confirms the underlying mechanism resolves the override correctly (see Defect 5 for why this doesn't satisfy AC10 as written).
6. `grep` across `tests/` and `airun/` for any reference to `ai-role-baseline` fixtures or `AI_ROLE_DRYRUN` — none found.
7. Manual smoke test: `./bin/ai-next --dry-run` against the actual repository `project-state.md` — fails with `Invalid state: Missing required fields ... 'Review'`, exit 4.

## Acceptance criteria results

| AC | Description | Result |
|---|---|---|
| 1 | 6-step scenario completes under `ai-run-phase`, exit 0, `total_runs==6`, correct runner sequence | **FAIL** — harness cannot execute (Defects 1–3) |
| 2 | `ai-run-phase` exits 0 without starting next phase when Active Phase changes | **FAIL** — no assertion tests this; the one attempted scenario never reaches the phase-changing step (Defects 1–3) |
| 3 | Two-phase `ai-run` scenario: second phase's first Implementer resolves to `implementer`, not `senior_implementer` | **FAIL** — no test exists |
| 4 | Four Debugger requests in one phase stop at third `senior_debugger`, exit 2, rule §8 | **FAIL** — no test exists |
| 5 | 15-execution scenario stops before 16th, exit 2, rule §20 | **FAIL** — no test exists |
| 6 | `Next Role: Architect` stops both loops, exit 2 | **FAIL** — no test exists |
| 7 | `Human Intervention Required: Yes` stops both loops, exit 2 | **FAIL** — no test exists |
| 8 | Non-zero runner exit stops both loops, exit 3, no retry | **FAIL** — no test exists |
| 9 | Manual alias invocation (`o-dev`, `c-test`, `c-rev`, `o-git`, etc.) still works via `AI_ROLE_DRYRUN=1` | **FAIL** — no test references `AI_ROLE_DRYRUN` or the `ai-role-baseline` fixtures anywhere |
| 10 | Project-local `.ai-run.json` reassigns a runner; verified as a tested guarantee | **FAIL** — fixture exists but is never invoked by any test |
| 11 | `project-state.md` in every fixture free of orchestrator counters/history after harness runs | **FAIL** — unverifiable; harness never completes a run |
| 12 | README documents commands, config, runtime files, stop exit codes, runner reassignment | **PASS** — all elements present in `README.md` |

**1 of 12 acceptance criteria met.**

## Defects found

### Critical — Phase 8 test harness crashes immediately, never executes

`tests/test_phase8.py::setup_test_directory()` has no `return` statement, but `test_ai_run_phase()` calls it as `test_dir, ai_platform = setup_test_directory()`. Running `python3 tests/test_phase8.py` raises `TypeError: cannot unpack non-iterable NoneType object` before a single assertion runs. The deliverable's only acceptance script for Phase 8 has never successfully executed.

**Failure scenario:** `python3 tests/test_phase8.py` → traceback, exit 1, zero test coverage delivered despite the file's presence.

### Critical — Stub runner has no mechanism to advance scenario steps across process invocations

`tests/stub/stub-runner.py` reads the step index only from the `STUB_STEP` environment variable (line 25) and never writes it back anywhere (no step-counter file, no state persisted between runs). Each role invocation is a fresh `subprocess.run` (`airun/launcher.py:launch_runner`) that copies `os.environ` from the parent `python -m airun` process — which itself inherited `STUB_STEP=0` once, at test setup, and never changes it. Every single stub-runner invocation across an entire multi-step scenario therefore replays step 0 only.

**Failure scenario:** even with Defect 1 fixed, the first `ai-next` call runs step 0 ("Implementer completes successfully", sets `Next Role: Tester`, exit 0) — progress is made, so `ai-next` returns 0. The second `ai-next` call resolves `tester`, but the stub again runs step 0 and sets `Next Role: Tester` again — an unchanged value. `airun.launcher.check_progress` then reports no progress, and `ai-next` returns exit 2 ("No progress: Tester returned same Next Role: Tester"). The 6-step scenario required by AC1 can never be driven to completion by this harness as built.

### Critical — Scenario step 2 encodes a QA failure as a non-zero process exit, which the orchestrator treats as a runtime failure, not a routing transition

`tests/stub/scenario-implementer-to-git.json` step 2 ("Tester fails") sets `"exit_code": 1` to represent the Tester finding a defect and handing to Debugger. But `next_command` in `airun/__main__.py` (lines 216–223, exercising `airun/launcher.py`) treats *any* non-zero child exit as a runtime failure: it prints "Runtime failure: ..." and returns exit 3 immediately, without inspecting `Next Role` at all — this is the same non-retry behavior verified for Phase 7 AC6. A QA FAIL that hands off to Debugger must be represented by the role process exiting 0 with `Next Role: Debugger` in `project-state.md`, exactly as Phase 7's own semantics require.

**Failure scenario:** even with Defects 1–2 fixed, the scenario would halt at step 2 with exit 3 ("Runtime failure: Tester (tester) exited 1") instead of proceeding to Debugger, Tester(PASS), Reviewer, and Git Assistant. The scenario file is internally inconsistent with the orchestrator semantics it is meant to exercise.

### Critical — The repository's own `project-state.md` is invalid against the schema the Phase 8 code enforces

The canonical template (`templates/project-state.md`) and `airun/state.py`'s `required_fields` list both require a `Review` field in the `## Execution` section. Commit `16d6b2b` ("Update project-state.md for handoff to Tester" — the Implementer's own Phase 8 handoff) deleted this field from the repository root `project-state.md` without a schema change being instructed, violating `role-lifecycle.md`'s "Do not add new fields or sections unless explicitly instructed to change this schema" (removal is the same violation in reverse — the schema was silently altered).

**Failure scenario:** `./bin/ai-next --dry-run`, run against the actual repository right now, fails with `Invalid state: Missing required fields in .../project-state.md: 'Review' (expected in section 'Execution')` and exits 4. The pre-existing regression test `tests.test_state.TestProjectStateParser.test_parses_current_project_state` fails as a direct, reproducible consequence. The orchestrator cannot currently drive its own project — a self-hosting failure in the exact file this QA task was activated from.

### High — Runner-override fixture (AC10) created but never exercised by any test

`tests/fixtures/runner-override-project/.ai-run.json` exists and, on manual verification, the underlying merge logic in `airun/config.load_config` resolves it correctly (confirmed: `reviewer` command resolves to the fixture's override, `phase_max_executions` resolves to 20, and a project without the override still resolves the global config — verified by code inspection of the merge logic, which is unconditional per-key overlay). However, AC10 explicitly requires this be "a tested guarantee, not documentation," and no test file references this fixture at all. The underlying mechanism appears sound, but the AC as written is unmet.

### High — AC9 (manual alias invocation via `AI_ROLE_DRYRUN=1`) has zero test coverage

`bin/ai-role` does implement `AI_ROLE_DRYRUN` (line 196) and Phase 1's baseline fixtures (`tests/fixtures/ai-role-baseline/*.txt`) exist, but no Phase 8 test (or any test) invokes `ai-role` with `AI_ROLE_DRYRUN=1` against those fixtures. AC9 is a regression guarantee that manual alias invocation still works unchanged after the loop commands were added — this is entirely unverified.

## Overall outcome

**FAIL**

4 Critical defects, 2 High defects. 11 of 12 acceptance criteria unmet — the Phase 8 test harness has never successfully executed once, and the one scenario it defines could not reach completion even if its crash were fixed, due to two further, independent bugs in the harness's step-advancement and exit-code semantics. Separately, the actual repository `project-state.md` — updated by this same handoff — is invalid against the schema the Phase 8 code itself enforces, breaking a pre-existing regression test and the orchestrator's ability to run against its own project. Implementation is not ready to proceed to Reviewer; returning to Debugger.
