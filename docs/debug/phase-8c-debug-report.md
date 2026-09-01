# Phase 8c Debug Report

**Branch:** feature/phase-8c
**QA Report:** docs/qa/phase-8c-qa-report.md

---

## Issue Investigated

**Defect 1 — Architect stop returns exit 0 instead of exit 2/§12 (High)**

Both `run_phase_command` and `run_command` in `airun/__main__.py` treated `Next Role: Architect` identically to workflow-idle completion, returning exit 0 with "Workflow completed" instead of exit 2 with rule §12.

## Root Cause

After a successful `next_command()` call (which launched the Implementer stub), both loop commands re-read `project-state.md` and short-circuited on the Architect check before the next loop iteration could call `next_command()` again — where `resolve()` would correctly classify Architect as `action="stop"` with rule §12 and return exit 2.

`run_phase_command` (line 304): `next_role_lower == "architect" or not next_role_lower`
`run_command` (line 351): `next_role_lower in ("architect", "", "none")`

Origin: `run_phase_command`'s conflation was introduced in Phase 8a (commit `8570710`); `run_command` mirrored it in a Phase 8a debug fix (commit `5951300`).

## Files Modified

| File | Change |
|------|--------|
| `airun/__main__.py:304` | Removed `"architect"` from `run_phase_command` short-circuit; only empty `Next Role` triggers idle completion |
| `airun/__main__.py:351` | Removed `"architect"` from `run_command` short-circuit; only `""` and `"none"` trigger idle completion |
| `tests/test_phase8c.py:207-212` | Changed `returncode` assertion from `0` to `2`; added §12 output check |

## Corrective Actions

Removed the Architect-specific short-circuits from both loop commands. Architect is now handled exclusively by `next_command`, which calls `resolve()` and returns exit 2 with rule §12. The idle completion checks (empty/None `Next Role`) are preserved.

## Verification

- `python3 tests/test_phase8c.py` — all 3 ACs pass (Architect exits 2 with §12, human intervention exits 2 with §13, runner failure exits 3)
- Full regression suite passes: `test_state.py` (10), `test_routing.py` (24), `test_phase3.py` (15), `test_phase8.py`, `test_phase8b.py`
- No changes to `airun/routing.py` — the routing engine was already correct

## Remaining Known Issues

None.