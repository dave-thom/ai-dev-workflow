# Debug Report — Phase 1 Defect 1

---

## Issue Investigated

Stale `o-git` regression baseline fixture (`tests/fixtures/ai-role-baseline/o-git.txt`) causing AC 3 failure.

---

## Root Cause

The baseline fixture was captured before `prompts/role-git.md` received the Phase Advancement
responsibility section. Both changes (role-git.md update and fixture capture) landed in the
same commit `65217e8`. The fixture reflects the pre-update content of `role-git.md`, so the
committed baseline does not match the post-Phase-1 prompt content.

The fixture missed 13 lines comprising:

* A `# Phase Advancement` heading
* 4 enumerated steps
* An explanatory paragraph
* A thematic-break separator

---

## Files Modified

| File | Change |
|---|---|
| `tests/fixtures/ai-role-baseline/o-git.txt` | Recaptured via `AI_ROLE_DRYRUN=1 ai-role opencode git -m openrouter/deepseek/deepseek-v4-flash` |

---

## Corrective Actions

Recaptured the fixture from the current post-Phase-1 `prompts/role-git.md` using the
dry-run capture mechanism already used for the other 11 alias forms.

---

## Remaining Known Issues

None.