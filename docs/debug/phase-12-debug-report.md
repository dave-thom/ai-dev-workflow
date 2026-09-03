# Phase 12 Debug Report — Debugger Tier Retirement

Branch: `phase-12-debugger-tier-retirement`
Source QA Report: `docs/qa/phase-12-qa-report.md`

---

## Defect 1 — Critical: .gitignore missing orchestrator runtime files

**Root cause:** `.gitignore` was rewritten across commits `62a9076` and `003e6c0`. The entries for `.ai-run-state.json` and `.ai-run.log` (added in Phase 1, required by Phase 1 AC 6, enforced by the ignore guard in `guards.py`) were dropped and never restored.

**Fix:** Restored `.ai-run-state.json` and `.ai-run.log` to `.gitignore`.

**File modified:** `.gitignore`

---

## Defect 2 — High: tests/test_phase3.py stale debugger-role assertion

**Root cause:** `test_load_global_config` still asserted `"debugger"` is a key in `config["roles"]`. Phase 12 removed the `debugger` role from `config/ai-run.json`, so the assertion now fails.

**Fix:** Removed `"debugger"` from the `expected_roles` list in `test_load_global_config`.

**File modified:** `tests/test_phase3.py`

---

## Defect 3 — Medium: Phase 12 AC3 override guarantee untested

**Root cause:** No automated test exercised project-local override of `senior_debugger`.

**Fix:** Added `test_override_senior_debugger` to `TestConfigLoading` in `tests/test_phase3.py`. The test creates a temp environment with a global config containing all seven post-retirement roles, overlays a local `.ai-run.json` that overrides `senior_debugger` with `["custom-debug-tool"]`, and asserts the merged config uses the local override and has no `debugger` key.

**File modified:** `tests/test_phase3.py`

---

## Verification

- `git check-ignore` confirms `.ai-run-state.json` and `.ai-run.log` are ignored.
- `./bin/ai-next --dry-run` exits 0 (was 4).
- All 50 `tests/` unit tests pass.
- All root-level acceptance suites (`test_phase2_ac.py` through `test_phase6_ac.py`) pass.
- All integration test suites (`tests/test_phase8.py`, `tests/test_phase8b.py`, `tests/test_phase8c.py`, `tests/test_phase9.py`, `tests/test_phase11.py`) pass.

---

## Not Addressed

- **Defect 4** (test_phase10.py): Predates Phase 12, not caused by the debugger-routing change. Flagged for informational purposes only. Not blocking re-test.