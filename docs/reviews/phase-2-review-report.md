# Review Report — Phase 2: Project State Parser

---

## Scope Reviewed

`airun/state.py`, `airun/errors.py`, `airun/__init__.py`, `tests/test_state.py`,
`tests/fixtures/state/*.md`, `templates/project-state.md`, against `myplan.md` §3
(`state.py` component responsibilities) and Phase 2 acceptance criteria, following
QA PASS recorded in `docs/qa/phase-2-qa-report.md`.

---

## Overall Decision

**APPROVE**

All 8 Phase 2 acceptance criteria pass, the implementation matches the planned
interface (`ProjectState`, `read_project_state`, `progress_snapshot`), uses only the
standard library, and performs no writes or inference. No Critical or High findings.
Three Low findings are recorded for future cleanup; none block acceptance.

---

## Findings

### 1. Low — Silent no-op guard in `test_parses_current_project_state`

`tests/test_state.py:141` guards the entire test body with `if state_path.exists()`,
so the test passes trivially (no assertions run) in any environment where
`project-state.md` is absent from the repo root. This exact pattern was the root
cause of Defect 2 in `docs/debug/phase-2-debug-report.md` — a wrong path silently
suppressed the test body rather than failing loudly. The path is now corrected, but
the fragile pattern that caused the original miss is still in place.

**Recommendation:** replace the `if exists()` guard with `self.skipTest(...)` when
the file is absent, so a future path regression shows as a skipped test rather than
a silent pass.

### 2. Low — Unused import in `state.py`

`from collections import defaultdict` (`airun/state.py:4`) is imported but never
used; `parsed` is a plain `dict`.

**Recommendation:** remove the unused import.

### 3. Low — Document preamble scanned as a pseudo-section

The section splitter treats any line starting with `#` as a section header,
including the document's H1 title (`# PROJECT STATE`). The prose between the title
and the first `---` is therefore scanned by the same field regex as real sections.
Today this is harmless because that prose contains no colons, but a future edit to
the boilerplate description (e.g. "See spec: file.md") would silently be captured
into `raw` as a field, and — if it happened to collide with a real field's name in a way that
duplicates it — would fail parsing with a confusing "duplicate field" error.

**Recommendation:** either restrict field scanning to sections whose header starts
with `##` (matching the actual template structure), or explicitly skip content before
the first `---` delimiter. Not blocking: `project-state.md`'s own governance rules
prohibit unreviewed edits to its structure, which contains this risk today.

---

## Architectural Compliance

* Matches the planned interface in `myplan.md` §3 exactly: `ProjectState` NamedTuple
  fields, `read_project_state(path) -> ProjectState`, `progress_snapshot(state) -> dict`.
* No writes, no repair, no inference — consistent with the plan's parsing rules.
* `state.py` imports only `re`, `collections`, `typing`, and `airun.errors` — stdlib
  only, matching the Phase 2 scope and AC8.
* `errors.py` additionally defines `StopRequired`, scoped for Phase 3 use. This is
  scope slightly ahead of Phase 2, but it is inert (unused by any Phase 2 code path)
  and avoids churn when Phase 3 begins — not a defect.

---

## Maintainability

Straightforward, single-purpose module; regex-based line parsing is easy to follow.
The three Low findings above are the only maintainability observations.

---

## Recommendation

Accept Phase 2 as delivered. Address the three Low findings opportunistically (e.g.
during Phase 3 work touching `state.py`/`test_state.py`), but do not gate progress on
them.
