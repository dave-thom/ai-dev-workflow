# Debug Report — Phase 9 Defect 1

**Issue:** Runtime-failure detection silently removed (High)

**Source:** `docs/qa/phase-9-qa-report.md` — Defect 1

---

## Root Cause

During the Phase 9 refactor of `next_command` in `airun/__main__.py`, the
Implementer moved the `process.returncode` check to *before* the
state-reload/log-reorder fix for AC5. The check was then inadvertently deleted
when the code was restructured a second time (the final version has
`launch_runner` → state-reload → done-log → guardrail → progress-check, with
no `returncode` check anywhere).

The check that was removed:

```python
if process.returncode != 0:
    print(f"Runtime failure: {decision.logical_role} ({decision.runner}) "
          f"exited {process.returncode}", file=sys.stderr)
    return 3
```

A crashing runner fell through to the "no progress" check, which misreported
the crash as a stall (exit 2) instead of a runtime failure (exit 3).

---

## Files Modified

`airun/__main__.py` — re-inserted the `process.returncode != 0` check between
`launch_runner` return and the state reload at line 207, preserving both the
defect fix and the AC5 log ordering fix.

---

## Corrective Actions

- Restored the `process.returncode != 0` check, printing "Runtime failure" to
  stderr and returning exit code 3, immediately after `launch_runner` returns.
- The check is placed *before* the state reload, so a crashing runner does not
  read stale post-crash state or log a misleading "done" entry.

---

## Verification

- `tests/test_phase8c.py` — AC3 (Runner Failure Stop) passes for both
  `ai-run-phase` and `ai-run` (exit 3, "Runtime failure" in output).
- `tests/test_phase9.py` — all 4 test functions pass.
- `tests/test_phase8.py` — all pass (full scenario, runner override, dry-run).
- `tests/test_phase8b.py` — Phase Boundary, Cross-Phase, Debugger Limit,
  Phase Limit — all pass.

---

## Remaining Known Issues

None. The defect is resolved.