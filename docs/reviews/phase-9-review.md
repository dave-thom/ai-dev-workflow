# Phase 9 Review — Invocation Parity and Log Correctness

**Branch:** main (uncommitted working tree)
**Inputs:** `docs/qa/phase-9-qa-report.md` (FAIL, Defect 1), `docs/debug/phase-9-defect-1.md`,
`docs/qa/phase-9-defect-1-retest.md` (PASS), `myplan.md` Phase 9 acceptance criteria 1–6.

---

## Verification performed

Independently re-ran, rather than relying solely on the QA reports:

1. `python3 tests/test_phase9.py` — all 4 acceptance checks pass.
2. `python3 tests/test_phase8c.py` — all 3 ACs pass, including AC3 (Runner
   Failure Stop, exit 3) for both `ai-run` and `ai-run-phase`.
3. `python3 tests/test_phase8.py` — full suite passes.
4. Read `airun/__main__.py:198–213` — confirms the `process.returncode != 0`
   check sits between `launch_runner` and the state reload, so a crash is
   caught before `new_project_state` is read and before any `done` log line
   is written. This preserves both the Defect 1 fix and the AC5 log-ordering
   fix without reintroducing the original bug (stale state read after crash).
5. Read the full diff of `airun/config.py`, `airun/launcher.py`, `bin/ai-role`,
   `config/ai-run.json`, `tests/test_phase8.py` against the Phase 9 scope
   declared in `myplan.md`.

## Acceptance criteria

All 6 Phase 9 acceptance criteria are met, confirmed independently:

| AC | Result |
|---|---|
| 1 — OpenCode batch dry-run: `opencode run`, no `--auto`, no kickoff | PASS |
| 2 — Message byte-identical to manual baseline | PASS |
| 3 — Non-batch dry-run reproduces all 12 baseline fixtures byte-for-byte | PASS |
| 4 — Claude batch invocation unchanged | PASS |
| 5 — `done` log line reports post-execution `Next Role` | PASS |
| 6 — Phase 8 baseline check fails on any byte difference | PASS |

## Defect 1 (High) — resolution confirmed

The regression QA found (runtime-failure detection silently dropped from
`next_command`, causing crashes to be misreported as "no progress"/exit 2
instead of exit 3) is genuinely fixed. The restored check is correctly
ordered relative to the AC5 fix, and `tests/test_phase8c.py` AC3 passes for
both `ai-run` and `ai-run-phase`. No further interaction issues with Phase 9
were observed.

## Findings

### Low — inconsistent indentation in `bin/ai-role`

**Location:** `bin/ai-role`, the two OpenCode `if [[ "${AI_ROLE_BATCH:-0}" ==
"1" ]]; then` blocks (dry-run branch and real-execution branch, each
replacing the old `--auto`/last-arg-splitting logic).

Both `if` lines sit at column 0 instead of matching the surrounding
`case`/`opencode)` indentation, and the corresponding `else`/`fi` keep the
original deeper indent. Bash doesn't care, and all tests pass, but it's a
readability regression in a file that was otherwise consistently indented.

**Recommendation:** re-indent both blocks to match the surrounding `case`
arm on the next pass through this file. Not blocking.

## Architectural / scope compliance

Changes are confined to the declared Phase 9 scope (`bin/ai-role`,
`airun/launcher.py`, `airun/config.py`, `airun/__main__.py`,
`config/ai-run.json`, `tests/test_phase8.py`, `tests/test_phase9.py`) plus
the Defect 1 fix, which QA correctly identified as an unintended side effect
of the same refactor and the Debugger correctly scoped as a targeted,
minimal restoration. No speculative changes, no scope creep.

## Decision

**APPROVE**

0 Critical, 0 High, 0 Medium, 1 Low (non-blocking, cosmetic). All 6
acceptance criteria met, the prior blocking defect is resolved and verified
independently, and no regressions were found across the Phase 9, 8, and 8c
suites.
