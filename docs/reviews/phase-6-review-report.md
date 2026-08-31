# Review Report — Phase 6: Guards

---

## Decision

**APPROVE**

---

## Scope Reviewed

`airun/guards.py` (`check_git_handoff_guard`), its wiring into
`airun/__main__.py:next_command` (`--dry-run` + `Next Role: Tester` path),
against `myplan.md` Phase 6 section (lines 450–468) and its 8 acceptance
criteria. Inputs: QA Findings Report `docs/qa/phase-6-qa-report.md` (PASS,
two Low defects, both carried forward from Phase 5), completed
implementation (uncommitted working tree), approved plan `myplan.md`.

---

## Findings

### High / Medium

None.

### Low

1. **Ignore guard still runs after state parse/routing, not "at startup"**
   (`airun/__main__.py:120–128`) — carried forward from the Phase 5 review
   and QA report, unchanged. No AC violated. Same Phase 7 remediation note
   applies: when live execution is added, both guards should move ahead of
   state/config loading to match the documented contract.

2. **Stray non-scope files still uncommitted**: `project-state-backup.md`
   and `test-project-state.md`, first flagged in the Phase 5 review, remain
   untracked and unused by any guard. Carried forward again for the Git
   Assistant's handoff.

3. **`check_git_handoff_guard`'s outer exception handling is inconsistent
   between its three checks** (`airun/guards.py:46–151`): the branch check
   and status check each wrap a single `subprocess.run(..., check=True)` in
   its own `try/except subprocess.CalledProcessError`, while the upstream
   check nests a second `try/except subprocess.CalledProcessError` for the
   fetch/compare inside the outer upstream `try` block — and neither path
   catches `FileNotFoundError` (raised if `git` itself is missing from
   `PATH`), unlike `check_ignore_guard`'s repo-detection check just above it
   in the same file, which catches `(subprocess.CalledProcessError,
   FileNotFoundError)`. In the unlikely event `git` is unavailable after the
   initial `rev-parse --git-dir` probe succeeds (e.g. `PATH` mutated
   mid-process), the guard would raise an uncaught exception instead of
   returning a message, which `next_command`'s outer `try` would catch only
   via the generic exception handler (exit 1) rather than the guard's
   intended exit 2. Not exercised by any acceptance criterion; theoretical
   rather than observed. Non-blocking.

---

## Verification Performed

* Re-read `airun/guards.py` (`check_git_handoff_guard`) and the Phase 6
  wiring in `airun/__main__.py:133–139` in full against the plan's 8
  acceptance criteria.
* Re-ran `PYTHONPATH=$(pwd) python3 -m unittest discover -s tests -p
  "test_*.py"` — 49/49 pass, no regressions.
* Re-ran `python3 test_phase6_ac.py` — all 8 ACs plus the AC8 control case
  pass (9/9), independently confirming QA's results.
* Confirmed AC6/AC5 scoping by reading `airun/__main__.py:133`: the guard is
  gated on `args.dry_run and decision.action == "launch" and
  decision.logical_role.lower() == "tester"` — matches "not applied when
  `Next Role` is anything other than Tester" and the plan's dry-run-only
  scope for Phase 6 (live launching deferred to Phase 7).
* Confirmed AC7 by reading every subprocess call in `check_git_handoff_guard`
  and `check_ignore_guard`: only `rev-parse --git-dir`, `symbolic-ref
  --short HEAD`, `status --porcelain`, `rev-parse --abbrev-ref
  --symbolic-full-name @{u}`, `fetch`, `rev-parse HEAD`, `rev-parse
  <remote>/<branch>`, and `check-ignore -q` appear — no `add`, `commit`,
  `push`, `checkout`, or `reset` anywhere in the file.
* Confirmed the upstream-ref parse (`remote, branch =
  upstream_ref.split("/", 1)`) correctly handles a branch name that itself
  contains `/` (e.g. `origin/feature/foo`) via `maxsplit=1`.
* Confirmed all subprocess calls pass argument lists (no `shell=True`).
* Confirmed exit code 2 is returned on guard violation
  (`airun/__main__.py:136–139`), matching the plan's "role-contract
  violation" exit code, distinct from the ignore guard's exit 4.
* Confirmed no guard, routing, or runtime logic outside Phase 6's declared
  scope (`airun/guards.py`, its `__main__.py` wiring) was altered;
  `airun/routing.py` and `airun/runtime.py` are unchanged from Phase 4/5.

---

## Rationale

No Critical, High, or Medium findings. All 8 Phase 6 acceptance criteria
independently re-verified passing, with no regressions across all prior
phases' suites. Two Low findings are carried forward, already known and
non-blocking; the third (inconsistent exception handling for a
`FileNotFoundError` edge case) is theoretical, not exercised by any
acceptance criterion, and does not affect correctness of the documented
guard contract. Per review philosophy, Low findings do not block approval.

---

## Recommendation

Proceed to phase advancement (Git Assistant): commit the Phase 6
deliverables (`airun/guards.py`, `airun/__main__.py`, `test_phase6_ac.py`,
the updated `test_phase5_ac.py`, QA and review reports), excluding
`project-state-backup.md` and `test-project-state.md`, and advance
`Active Phase` to Phase 7 (Live Single-Step Execution) per `myplan.md`.
