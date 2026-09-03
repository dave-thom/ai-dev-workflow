# Phase 9 QA Report — Invocation Parity and Log Correctness

**Branch:** main (uncommitted working tree)
**Scope:** `bin/ai-role`, `airun/launcher.py`, `airun/__main__.py`,
`config/ai-run.json`, `tests/test_phase8.py`, `tests/test_phase9.py`, per
`myplan.md` Phase 9 acceptance criteria 1–6.

---

## Tests performed

1. `python3 tests/test_phase9.py` — the Implementer's new Phase 9 suite. All four
   test functions pass.
2. `python3 tests/test_phase8.py` — full Phase 8 suite (ai-run-phase loop,
   runner-override merge, `AI_ROLE_DRYRUN` baselines). All pass.
3. Manual, independent reproduction of AC3: wrote a standalone script
   (outside any test harness) that invokes `bin/ai-role` directly with
   `AI_ROLE_DRYRUN=1` and no `AI_ROLE_BATCH`, for all twelve baseline aliases in
   `tests/fixtures/ai-role-baseline/` (`c-design`, `c-pdebug`, `c-rev`, `c-sdev`,
   `c-ta`, `c-test`, `o-debug`, `o-dev`, `o-devr1`, `o-git`, `o-sdebug`,
   `o-sdev`), comparing stdout byte-for-byte against each fixture. All twelve
   match exactly. (Note: the plan text says "eleven aliases" but twelve fixture
   files exist and are covered; pre-existing wording in `myplan.md`, not a
   defect in this implementation.)
4. Read the AC5 fix directly (`airun/__main__.py:198–218`): `new_project_state`
   is now read immediately after `launch_runner` returns and before the `done`
   log line is written, so the line logs the post-execution `Next Role`. This
   matches AC5's example (`airun/__main__.py:213` in the pre-fix code).
5. Read the AC6 fix (`tests/test_phase8.py`, `test_ai_role_dryrun`): the lenient
   fallback (`lines[:2] == exp_lines[:2]` plus marker presence) was removed;
   a byte mismatch now prints a diff and returns `False` unconditionally.
6. Full regression suite: `tests/test_state.py` (10), `tests/test_routing.py`
   (24), `tests/test_phase3.py` (15), `tests/test_phase8b.py` — all pass.
7. `tests/test_phase8c.py` — **fails**. See Defect 1.
8. `bash -n bin/ai-role` — syntax valid.
9. `python3 -c "import json; json.load(open('config/ai-run.json'))"` — valid
   JSON; every role carries an explicit `kickoff` value matching AC1/AC4
   (OpenCode roles `false`, Claude roles `true`).
10. Confirmed `launch_runner`'s new `kickoff_enabled` parameter has exactly one
    call site (`airun/__main__.py:200`), already updated to match the new
    signature — no other caller left on the old 3-arg form.
11. Diffed the full working tree against `HEAD` and confirmed only files in the
    Implementer's declared Phase 9 scope changed, with one exception: the
    removal of the runtime-failure check in `next_command` (Defect 1) falls
    outside the described change ("reload state, fix the `done` log line") and
    is an unintended side effect of that edit, not a scoped change.

## Acceptance criteria results

| AC | Description | Result |
|---|---|---|
| 1 | `AI_ROLE_DRYRUN=1 AI_ROLE_BATCH=1` for every OpenCode role emits `opencode run` with no `--auto`, message = composed lifecycle + role prompt, no kickoff text | PASS |
| 2 | That message is byte-identical to the manual baseline body | PASS |
| 3 | `AI_ROLE_DRYRUN=1` without `AI_ROLE_BATCH` reproduces every committed baseline byte-for-byte | PASS (all 12 fixtures verified) |
| 4 | Claude roles under batch still emit `claude -p --append-system-prompt … "<kickoff>"`, unchanged | PASS |
| 5 | The `done` log line reports `Next Role` read after execution | PASS |
| 6 | The Phase 8 baseline check fails on any byte difference | PASS |

**6 of 6 acceptance criteria met.**

## Defects found

### Defect 1 — Runtime-failure detection silently removed (High)

**Location:** `airun/__main__.py`, `next_command` (around line 198–218).

While restructuring `next_command` to fix AC5 (read `new_project_state` before
logging), the Implementer deleted the runtime-failure check that previously
followed `launch_runner`:

```python
if process.returncode != 0:
    print(f"Runtime failure: {decision.logical_role} ({decision.runner}) "
          f"exited {process.returncode}", file=sys.stderr)
    return 3
```

This check is gone from the current code entirely — `process.returncode` is
now referenced only inside the `done` log line, never checked. A crashing
runner no longer stops the loop with exit 3; execution instead falls through
to the "no progress" check, which reports the wrong condition and exits 2.

**Reproduction:** `python3 tests/test_phase8c.py` — `AC 3: Runner Failure
Stop` fails:

```
Stub: Updated project-state.md (step=0)
  description: Implementer crashes with non-zero exit
  exit_code: 1
No progress: implementer returned same Next Role: Implementer
AssertionError: [ai-run-phase] Expected 3, got 2
```

`tests/test_phase8c.py` is unmodified by this change (`git diff --stat HEAD --
tests/test_phase8c.py` is empty) and was passing at the Phase 8c QA pass
(`docs/qa/phase-8c-qa-report.md`, commit `44d840d`). This is a regression, not
a pre-existing gap.

**Impact:** both `ai-run` and `ai-run-phase` share `next_command`, so a
crashed runner under either command is now misreported as "no progress"
(exit 2) instead of "Runtime failure … exited N" (exit 3). This defeats the
§13-adjacent stop condition for runner crashes and could mask a genuine
crash as an ordinary stall during later debugging.

**Scope note:** this is outside Phase 9's declared scope (Phase 9 only calls
for reordering the state-reload and fixing the log line) — it is an
unintended side effect of the refactor, not a deliberate Phase 9 change.

## Overall outcome

**FAIL**

0 Critical, 1 High, 0 Medium, 0 Low defects. All 6 Phase 9 acceptance criteria
are individually met, but the implementation regresses a previously-passing,
previously-approved behavior (Phase 8c AC3 / runtime-failure stop with exit
3), which fails `tests/test_phase8c.py`. Per FAIL criteria, a High defect that
breaks existing, still-required functionality blocks progression. The fix
belongs with the Debugger: restore the `process.returncode != 0` check
(logging "Runtime failure" and returning 3) at the correct point in the
reordered `next_command` — after `launch_runner` returns but independent of
the `done`-log/`new_project_state` ordering fix — then re-run
`tests/test_phase8c.py` and `tests/test_phase9.py` together to confirm no
further interaction.
