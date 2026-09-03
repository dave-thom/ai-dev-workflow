# Phase 9 Retest — Defect 1 (Runtime-failure detection)

**Branch:** main (commit `effb7ce` — fix(debug): restore runtime-failure exit-3 check in next_command)
**Scope:** Retest of `docs/debug/phase-9-defect-1.md` fix; regression check against `docs/qa/phase-9-qa-report.md`.

---

## Tests performed

1. Read `airun/__main__.py:207-210` — confirmed the `process.returncode != 0`
   check is present, positioned immediately after `launch_runner` returns and
   before the state reload / `done` log line (preserves the AC5 ordering fix).
2. `python3 tests/test_phase8c.py` — all three ACs pass, including AC3
   (Runner Failure Stop): both `ai-run-phase` and `ai-run` exit 3 with
   "Runtime failure: implementer (implementer) exited 1" on stderr.
3. `python3 tests/test_phase9.py` — all Phase 9 acceptance checks pass
   (OpenCode dry-run batch mode, Claude kickoff, dry-run baseline byte
   comparison, done-log ordering, Phase 8 baseline strictness).
4. Regression: `tests/test_phase8.py`, `tests/test_phase8b.py` — pass.
5. Regression: `tests/test_state.py` (10), `tests/test_routing.py` (24),
   `tests/test_phase3.py` (15) — pass (run with `PYTHONPATH=.`; these three
   files lack the `sys.path` bootstrap the other suites have, a pre-existing
   environment quirk unrelated to this fix).

## Defect 1 status

**RESOLVED.** Runtime-failure detection (exit 3, "Runtime failure" message)
is restored and verified for both `ai-run` and `ai-run-phase`. No regressions
observed in Phase 9 acceptance criteria or the surrounding Phase 8/8b/8c/state/
routing suites.

## Overall outcome

**PASS**

0 Critical, 0 High, 0 Medium, 0 Low defects outstanding. All 6 Phase 9
acceptance criteria (per `docs/qa/phase-9-qa-report.md`) remain met, and the
Defect 1 regression is resolved with no new defects introduced.
