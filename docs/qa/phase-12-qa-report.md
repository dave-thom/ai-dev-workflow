# Phase 12 QA Report — Debugger Tier Retirement

Branch: `phase-12-debugger-tier-retirement`
Commits under test: `62a9076` (Phase 12), `003e6c0` (.gitignore cleanup)

---

## Scope Tested

Phase 12 acceptance criteria (`myplan.md`, §Phase 12) plus a full run of the
existing automated test suite to check for regressions, since `Implementation:
COMPLETED` implies the whole suite should be green.

## Tests Performed

* Ran all five root-level acceptance suites on `/usr/bin/python3`
  (`test_phase2_ac.py` … `test_phase6_ac.py`).
* Ran all nine suites under `tests/` (`test_state.py`, `test_routing.py`,
  `test_phase3.py`, `test_phase8.py`, `test_phase8b.py`, `test_phase8c.py`,
  `test_phase9.py`, `test_phase10.py`, `test_phase11.py`).
* Manually verified Phase 12 AC3 (project-local override of `senior_debugger`)
  with a functional script, since no automated test exercises it.
* Verified the `.gitignore` regression directly with `git check-ignore` and by
  running `./bin/ai-next --dry-run` in this repository.
* Diffed every file the Phase 12 commit touched against `main`.

## Acceptance Criteria Results (Phase 12, `myplan.md`)

| # | Criterion | Result |
|---|---|---|
| 1 | First `Next Role: Debugger` resolves to `senior_debugger` | PASS — `test_phase4_ac.py::test_ac3`, `tests/test_routing.py::test_debugger_first_call` |
| 2 | 2nd/3rd resolve to `senior_debugger`; 4th stops with exit 2, rule `§8` (3 total, not 4) | PASS — `tests/test_phase8b.py::test_debugger_limit` (senior_debugger=3, debugger=0, total_runs=3, stop on 4th request) |
| 3 | `config/ai-run.json` has no `debugger` role; project-local override of `senior_debugger` changes the resolved runner | PARTIAL — config correctly has no `debugger` role. The override behavior works (verified manually, see Defect 3) but is **not covered by any automated test**, contrary to the criterion's wording and the "tested guarantee, not documentation" standard set by Phase 8a AC3. |
| 4 | `.ai-run-state.json` retains `schema: 1`; `debugger` counter stays 0 across a phase with 3 debugger executions | PASS — `tests/test_phase8b.py::test_debugger_limit` confirms `debugger: 0`, `schema: 1` |
| 5 | `scenario-debugger-limit.json` updated to 3-execution ceiling; Phase 8b's other three scenarios pass unchanged | PASS — `tests/test_phase8b.py` full run exits 0 |
| 6 | README's runner table and debug sequence match amended §8 | PASS — `debugger` row removed from table; debug sequence text now describes the retired tier and the 3-execution ceiling |

## Defects

### Defect 1 — Critical: `.gitignore` no longer ignores orchestrator runtime files

`.gitignore` was rewritten across commits `62a9076` and `003e6c0`. The entries
for `.ai-run-state.json` and `.ai-run.log` (added in Phase 1, required by
Phase 1 AC 6 and enforced at the start of every orchestrator command via the
ignore guard in `guards.py`) were dropped and never restored — only
`__pycache__/`, `*.pyc`, `.DS_Store` and `**/.DS_Store` remain.

Confirmed live:

```
$ git check-ignore -q .ai-run-state.json ; echo $?
1
$ git check-ignore -q .ai-run.log ; echo $?
1
$ ./bin/ai-next --dry-run
Ignore guard violation: .ai-run-state.json and .ai-run.log must be git-ignored
exit=4
```

Every orchestrator command (`ai-next`, `ai-run-phase`, `ai-run`) now fails
immediately in this repository, including the branch's own subsequent
handoffs. This wasn't caught because the guard suites (`test_phase5_ac.py`,
`test_phase6_ac.py`) construct their own temporary repos with a correct
`.gitignore` — they never exercise the real one.

**Failure scenario:** running `ai-next --dry-run` (or any orchestrator
command) in this repository right now exits 4 with "Ignore guard violation",
regardless of `project-state.md` content.

### Defect 2 — High: `tests/test_phase3.py` regressed, not updated for Phase 12

`test_load_global_config` still asserts `"debugger"` is a key in
`config["roles"]`. Since Phase 12 removed that role, the test now fails:

```
AssertionError: 'debugger' not found in {...}
```

`tests/test_phase3.py` isn't in the Phase 12 plan's declared scope list, but
the change to `config/ai-run.json` broke it, and it went unnoticed —
`Implementation: COMPLETED` was declared without the full suite passing.

### Defect 3 — Medium: Phase 12 AC3's override guarantee is untested

Manual verification confirms the mechanism works:

```python
load_config(...)  # with a project-local .ai-run.json overriding senior_debugger
# -> roles['senior_debugger']['command'] == ['custom-debug-tool']
# -> 'debugger' not in roles
```

but no test in the suite exercises overriding `senior_debugger` specifically
(the existing runner-override test/fixture overrides `reviewer`). AC3 calls
this out as its own guarantee, distinct from AC generic override coverage
already delivered in Phase 8a.

### Defect 4 — Low, informational: files outside Phase 12's declared scope bundled into the commit

`tests/test_phase10.py` (new, 514 lines) and
`tests/stub/scenario-phase10-midphase-edit.json` (new) are not listed in
Phase 12's scope in `myplan.md` and are unrelated to debugger routing. They
appear to be recovered Phase 10 deliverables. Two of that file's own checks
(AC1, AC4) fail — a real conflict between Phase 10 (mid-phase `Active Phase`
edits must not stop the loop) and Phase 11's R4 invariant (which stops on any
such edit) — and the script masks this by exiting 0 even when it prints
"✗ Some Phase 10 tests failed". This predates Phase 12 and isn't caused by the
debugger-routing change, but it's part of the tree under test and affects
whole-suite health; flagging for visibility rather than scoring against
Phase 12.

## Outcome

**FAIL**

Phase 12's own routing/config/test/README changes are correct and every
directly-scoped acceptance criterion but AC3's test-coverage clause passes.
However, a Critical defect (Defect 1) makes the orchestrator unusable in this
repository as it stands, and a High defect (Defect 2) is an existing
automated test broken by this change and left unfixed. Per the FAIL criteria,
Critical or High defects block progression regardless of Phase-12-specific
results.

**Required before re-test:**

1. Restore `.ai-run-state.json` and `.ai-run.log` to `.gitignore`.
2. Fix `tests/test_phase3.py::test_load_global_config` to expect the seven
   post-retirement roles.
3. Recommended: add a test for Phase 12 AC3's override guarantee.
4. Recommended: resolve or explicitly defer the Phase 10/11 conflict
   surfaced by `tests/test_phase10.py`, and make its runner return a non-zero
   exit code on failure.
