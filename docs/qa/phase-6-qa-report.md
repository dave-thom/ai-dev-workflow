# Phase 6 QA Report — Guards

**Branch:** main (uncommitted working tree at time of test)
**Scope:** `airun/guards.py` (`check_git_handoff_guard`), its wiring into `airun/__main__.py`'s `next --dry-run` path, per myplan.md Phase 6.

---

## Tests performed

1. Full existing unit test suite: `python3 -m unittest discover -s tests -v` — 49 tests (`test_state.py`, `test_phase3.py`, `test_routing.py`). All pass, no regressions.
2. Regression check of prior phases' acceptance scripts: `python3 test_phase2_ac.py`, `test_phase3_ac.py`, `test_phase4_ac.py`, `test_phase5_ac.py` — all pass (8, 8, 15, 9 ACs respectively). `test_phase5_ac.py` was updated (uncommitted) to use `Next Role: Implementer` instead of `Tester` in scenarios not concerned with the handoff guard, and to add commits/upstream in the two scenarios that are still `Tester`-based (AC8, AC8-control) — a correct adaptation to the new Phase 6 guard, verified re-passing.
3. `test_phase6_ac.py` (already present, uncommitted): independent end-to-end acceptance script invoking the real `bin/ai-next` executable as a subprocess against disposable temporary git repositories — appropriate given Phase 6 is specifically about git-state guard behavior. Covers all 8 documented ACs plus a control case for AC8:
   - AC1: uncommitted modification present → exit 2.
   - AC2: committed but unpushed (no upstream) → exit 2, upstream-related message.
   - AC3: clean tree, upstream, local HEAD == upstream → exit 0, proceeds to launch.
   - AC4: no upstream configured → exit 2.
   - AC5: current branch ≠ `Git / Branch` in project-state.md → exit 2.
   - AC6: `Next Role: Implementer` and `Debugger`, no upstream → exit 0 (guard not applied to non-Tester roles).
   - AC7: behavioral check that `git log` and current branch are unchanged after a guard-passing run (consistent with code inspection — see below).
   - AC8: non-git working directory with `Next Role: Tester` → exit 2, clear message; control case with `Next Role: Implementer` in the same non-git directory → exit 0.
   All 9 (8 ACs + control) pass.
4. Static verification of AC7 (no mutating git commands) by reading `airun/guards.py` directly: `check_git_handoff_guard` issues only `rev-parse --git-dir`, `symbolic-ref --short HEAD`, `status --porcelain`, `rev-parse --abbrev-ref --symbolic-full-name @{u}`, `fetch`, and `rev-parse HEAD` / `rev-parse <remote>/<branch>`. `check_ignore_guard` issues only `rev-parse --git-dir` and `check-ignore -q`. No `add`, `commit`, `push`, `checkout`, or `reset` appears in either function — confirms AC7 by code, not just by behavior.
5. Verified guard scoping in `airun/__main__.py:133-139`: the handoff guard only runs when `args.dry_run` and `decision.action == "launch"` and `decision.logical_role.lower() == "tester"` — matches AC6's "not applied when Next Role is anything other than Tester," and matches the plan's Phase 6 scope of dry-run only (live launching is deferred to Phase 7).
6. Manual smoke test of `./bin/ai-next --dry-run` against the actual repository's current `project-state.md` (`Next Role: Tester`, `Active Phase: Phase 6`, clean/committed tree required) — confirms the guard integrates correctly with the live repo state, not just fixtures.

## Acceptance criteria results

All 8 acceptance criteria in myplan.md (Phase 6 section) verified PASS:

| AC | Description | Result |
|---|---|---|
| 1 | Uncommitted modification stops, exit 2 | PASS |
| 2 | Committed but unpushed stops, exit 2 | PASS |
| 3 | Clean tree + upstream + HEAD == upstream proceeds | PASS |
| 4 | No upstream configured stops, exit 2 | PASS |
| 5 | Branch mismatch stops, exit 2 | PASS |
| 6 | Guard not applied when Next Role ≠ Tester | PASS |
| 7 | No mutating git commands used | PASS |
| 8 | Non-git directory stops for Tester; ignore guard unaffected | PASS |

## Defects found

No Critical, High, or Medium defects.

### Low — carried forward from Phase 5: ignore guard still runs after state parse/routing, not "at startup"

Unchanged since the Phase 5 QA report (`docs/qa/phase-5-qa-report.md`): `check_ignore_guard` (line 128) and now `check_git_handoff_guard` (line 135) both still run after `read_project_state` and `resolve()` in `next_command`, not at the top of the function. No AC is violated by this (all Phase 5 and Phase 6 ACs pass), but a directory with a malformed `project-state.md` *and* a guard violation will report the state-parse error rather than the guard message. Non-blocking; opportunistic cleanup.

### Low — stray non-scope files still uncommitted, still not cleaned up

`project-state-backup.md` and `test-project-state.md` remain untracked in the repo root, first flagged in the Phase 5 QA report and still present unchanged. Confirmed again they are not read by any guard or by `ai-next`. Flagging again for the Git Assistant's handoff.

## Overall outcome

**PASS**

All 8 Phase 6 acceptance criteria satisfied, no Critical/High/Medium defects, all Phase 2–5 suites remain green with no regressions. Two Low-severity findings carried forward from Phase 5 (both pre-existing, neither newly introduced by Phase 6) do not block progression.
