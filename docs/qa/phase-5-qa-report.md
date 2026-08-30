# Phase 5 QA Report — `ai-next --dry-run`

**Branch:** main (uncommitted working tree at time of test)
**Scope:** `airun/__main__.py` (subcommand `next`, `--dry-run` only), `bin/ai-next`, `airun/logbook.py` (per myplan.md Phase 5)

---

## Tests performed

1. Full existing unit test suite: `PYTHONPATH=$(pwd) python3 -m unittest discover -s tests -p "test_*.py"` (equivalently, each file run directly) — 49 tests across `test_state.py`, `test_phase3.py`, `test_routing.py`. All pass, no regressions.
2. Regression check of prior phases' acceptance scripts: `python3 test_phase2_ac.py`, `python3 test_phase3_ac.py`, `python3 test_phase4_ac.py` — all pass (8, 8, 15 ACs respectively).
3. New independent acceptance script `test_phase5_ac.py`, written fresh against the myplan.md Phase 5 AC list (not derived from any Implementer test file — none existed for this phase). Unlike the unit-level tests for prior phases, this exercises the real `bin/ai-next` executable as a subprocess against disposable temporary working directories, since Phase 5 is specifically about CLI wiring end-to-end:
   - AC1: `bin/ai-next` file-mode and script-content check (executable bit, `PYTHONPATH` export, `exec python3 -m airun next "$@"`).
   - AC2/AC9: dry-run against a `Next Role: Tester` state — asserts all required output fields are present and exit code is 0.
   - AC3: printed `Command:` line compared byte-for-byte against `config/ai-run.json`'s `tester` command with the `kickoff_prompt` appended.
   - AC4: project-local `.ai-run.json` override points the `tester` runner at a script that writes a sentinel file; asserts the sentinel is never created.
   - AC5: asserts `.ai-run-state.json` and `.ai-run.log` are absent after a dry-run.
   - AC6: `Next Role: Architect` — asserts exit 2, active phase, status, the §12 stop reason, and a deliverable pointer (`Plan: myplan.md`) all appear in output.
   - AC7: malformed `project-state.md` (`# TEST` only, all required fields missing) — asserts exit 4.
   - AC8: fresh git repo with no `.gitignore` — asserts exit 4 and that both `.ai-run-state.json` and `.ai-run.log` are named in the output.
   - AC8 control: same setup but with a `.gitignore` covering both paths — asserts the run proceeds normally (exit 0), to confirm the guard isn't over-firing.
4. Manual smoke test of `./bin/ai-next --dry-run` against the actual repository's current `project-state.md` (`Next Role: Tester`, `Active Phase: Phase 5`) — correct output, exit 0, no stray files created (`git status --porcelain` unchanged apart from expected new test file).
5. Exploratory probes beyond the documented ACs:
   - Non-existent `project-state.md` (no file at all) → exit 4 (consistent with AC7's intent, though not literally "malformed").
   - Malformed state combined with un-ignored runtime paths in the same directory → still exits 4, but the message reports the state parse failure rather than the ignore-guard violation (see defect below).

## Acceptance criteria results

All 9 acceptance criteria in myplan.md (Phase 5 section) verified PASS, independently re-derived:

| AC | Result |
|---|---|
| 1–9 | PASS |

## Defects found

### Low — ignore guard does not run "at startup," contrary to its documented contract

`airun/__main__.py:99-131`: `project-state.md` is parsed and `config/ai-run.json` is loaded and validated, and routing is resolved, *before* `check_ignore_guard` is invoked. myplan.md's `guards.py` component spec states the ignore guard "runs at startup of every command, including dry-run." As implemented it runs last, immediately before printing.

**Failure scenario:** a directory with both a malformed `project-state.md` and un-ignored `.ai-run-state.json`/`.ai-run.log` produces `Invalid state: ...` (the state-parse error) instead of the ignore-guard message, even though the ignore-guard violation is also present. Exit code is 4 in both cases, so no AC is actually violated (AC7 and AC8 are never exercised in combination by the documented ACs), but a future caller relying on the specific message text to distinguish "fix your project-state.md" from "fix your .gitignore" would be misled in this combined scenario. Reordering the ignore-guard check to run first, before `read_project_state`, would align the code with its documented contract.

### Low — stray files outside Phase 5 scope left in the working tree

`project-state-backup.md` and `test-project-state.md` are untracked files in the repo root, evidently debugging artifacts from implementation. Neither is part of Phase 5's declared scope (`airun/__main__.py`, `bin/ai-next`, `airun/logbook.py`) and neither is referenced by any acceptance criterion. They don't affect `ai-next` behavior (confirmed: `ai-next` only ever reads `project-state.md` in the current working directory, never these files), but they are repository clutter that should not be committed. Flagging for the Git Assistant's handoff rather than blocking this phase.

No Critical, High, or Medium defects. The Phase 5 implementation working tree is currently uncommitted (`airun/__main__.py`, `airun/guards.py`, `airun/logbook.py`, `bin/ai-next` all show as untracked/modified in `git status`); this is expected at the Tester stage and is a Git Assistant concern, not a defect in the code itself.

## Overall outcome

**PASS**

All 9 acceptance criteria satisfied, no Critical/High/Medium defects, all existing Phase 2–4 test suites remain green, no regressions. The two Low-severity findings (guard ordering vs. documented contract; stray non-scope files) do not block progression but should be addressed opportunistically — the first ideally before Phase 6 (Guards) builds further on `guards.py`, the second by the Git Assistant before/at commit.
