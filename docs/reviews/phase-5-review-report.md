# Review Report — Phase 5: `ai-next --dry-run`

---

## Decision

**APPROVE**

---

## Scope Reviewed

`airun/__main__.py` (subcommand `next`, `--dry-run` only), `bin/ai-next`,
`airun/guards.py` (ignore guard only — the git handoff guard it also
contains is Phase 6 scope, not wired in), `airun/logbook.py`, against
`myplan.md` §3 (`__main__.py`, `guards.py`, `logbook.py`) and Phase 5
acceptance criteria (`myplan.md` lines 428–448). Inputs: QA Findings Report
`docs/qa/phase-5-qa-report.md` (PASS, two Low defects), uncommitted
implementation working tree.

---

## Findings

### High / Medium

None.

### Low

1. **Ignore guard runs at the end of the command, not at startup, and only
   inside the `--dry-run` branch** (`airun/__main__.py:99–131`). `myplan.md`
   documents the ignore guard as running "at startup of every command,
   including dry-run" (`## guards.py`), but `read_project_state`,
   `load_config`, `RuntimeState.load`, and `resolve` all execute first, and
   the check itself is nested under `if args.dry_run:` rather than called
   unconditionally. Already identified by QA. Confirmed no AC is currently
   violated (AC7 and AC8 exit 4 either way, since the malformed-state path
   returns before reaching the guard). Flagging the architectural angle for
   Phase 7: when live execution is added, the guard call as currently
   structured is dry-run-only and will need to be lifted out of that branch
   and moved ahead of state/config loading to match the documented contract,
   rather than duplicated. Non-blocking for Phase 5.

2. **Unused import** `log_event` in `airun/__main__.py:13`. `logbook.py` is
   correctly never invoked on the dry-run path (AC5 forbids it) and the
   real-execution stub is not yet implemented, so the import is currently
   dead code. No functional effect; remove or leave for Phase 7 wiring.

3. **Stray non-scope files in the working tree**: `project-state-backup.md`
   and `test-project-state.md` are untracked debugging artifacts, not part
   of Phase 5's declared scope or any acceptance criterion. Confirmed they
   are never read by `ai-next`. Already identified by QA; carried forward
   for the Git Assistant to exclude from the phase commit.

---

## Verification Performed

* Re-read `airun/__main__.py`, `airun/guards.py`, `airun/logbook.py`, and
  `bin/ai-next` in full against the Phase 5 plan section and the Phase 5
  acceptance criteria list.
* Re-ran `PYTHONPATH=$(pwd) python3 -m unittest discover -s tests -p
  "test_*.py"` — 49/49 pass, no regressions.
* Re-ran `python3 test_phase5_ac.py` — all 9 acceptance criteria pass.
* Confirmed `bin/ai-next` is executable, exports `PYTHONPATH`, and execs
  `python3 -m airun next "$@"` verbatim (AC1).
* Confirmed the printed `Command:` line is exactly the configured runner
  command plus the kickoff prompt appended as the final argument (AC3), and
  that overriding a runner via a project-local `.ai-run.json` changes the
  printed command with no source change (AC4's sentinel-script setup).
* Confirmed dry-run never calls `RuntimeState.save` or `log_event`, and that
  no `.ai-run-state.json` or `.ai-run.log` file is created (AC5) — verified
  by reading the code path, not only trusting the test result: `next_command`
  only calls `runtime.load` (read-only reconciliation in memory) and never
  `runtime.save` in the `--dry-run` branch.
* Confirmed exit-code mapping in `next_command` matches the plan's table for
  the paths Phase 5 implements: 0 (launch), 2 (stop, including Architect and
  routing stops), 4 (`InvalidStateError`, ignore-guard violation). The
  `StopRequired` handler (exit 2) and the generic exception handler (exit 1)
  are present but not currently reachable from any Phase 5 acceptance
  criterion — acceptable, since `resolve()` raises no exceptions and
  real execution (the only current source of a generic exception in this
  file) is explicitly deferred.
* Confirmed no guard, launcher, or routing logic was reimplemented or
  altered outside Phase 5's declared files; `airun/routing.py` and
  `airun/runtime.py` are unchanged from Phase 4/3.
* Confirmed subprocess calls in `guards.py` use argument lists (no
  `shell=True`), consistent with the plan's guard command allowlist.

---

## Rationale

No Critical, High, or Medium findings. All three Low findings are either
already caught by QA (guard ordering, stray files) or are trivial,
non-functional cleanliness items (unused import) with no current consumer
and no effect on any acceptance criterion. The implementation matches the
plan's interface and exit-code contract for everything Phase 5 is scoped to
deliver, all 9 Phase 5 acceptance criteria pass independently re-verified,
and all prior-phase suites remain green. Per review philosophy, Low findings
do not block approval.

---

## Recommendation

Proceed to phase advancement (Git Assistant): commit the Phase 5 deliverables
(`airun/__main__.py`, `airun/guards.py`, `airun/logbook.py`, `bin/ai-next`,
`test_phase5_ac.py`, QA and review reports), excluding
`project-state-backup.md` and `test-project-state.md`, and advance
`Active Phase` to Phase 6 (Guards) per `myplan.md`.
