# Debug Report — Phase 2

---

## Issue Investigated

Defects identified in `docs/qa/phase-2-qa-report.md`.

---

## Root Cause

### Defect 1 (High): `templates/project-state.md` missing

The file `templates/project-state(2).md` was committed in `fd6eb67` under the wrong filename, then deleted in `849a72b` ("Clean up stray file") instead of being renamed to the correct name `templates/project-state.md`. The correctly-named file was never created.

### Defect 2 (Low): Test path resolves above repo root

`tests/test_state.py:138` used `Path(__file__).parent.parent.parent`, which resolves one directory above the repository root (`dev-projects/` instead of `dev-projects/ai-dev-workflow/`). The `if state_path.exists()` guard silently suppressed the wrong path, causing the test body to never execute.

---

## Files Modified

| File | Change |
|---|---|
| `templates/project-state.md` | Created with content matching `tests/fixtures/state/valid-template.md` |
| `tests/test_state.py:138` | Changed `.parent.parent.parent` to `.parent.parent` |

---

## Corrective Actions

1. Created `templates/project-state.md` with the exact content from the test fixture `tests/fixtures/state/valid-template.md`.
2. Corrected the `project_root` path computation in `test_parses_current_project_state` from 3 levels up to 2 levels up.

---

## Verification

- `python3 -m unittest tests.test_state -v`: 10/10 passed
- `python3 test_phase2_ac.py`: 8/8 acceptance criteria passed (AC1 now passes)

---

## Remaining Known Issues

None.