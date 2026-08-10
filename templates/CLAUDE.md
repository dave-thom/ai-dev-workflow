# CLAUDE.md

Version: 2.1

---

# Purpose

This document defines the governance, engineering standards and operating principles for this project.

It applies to every AI role working within this repository.

Role behaviour is defined by **role-lifecycle.md**.

Role responsibilities are defined by the individual role definitions.

This document defines **how the project should be built**, not **how a role should execute**.

---

# Workflow Activation

`project-state.md` is the authoritative source of current workflow state and role activation.

AI roles may begin their assigned work automatically when all of the following are true:

* `project-state.md` identifies the active role as `Next Role`
* `Human Intervention Required` is `No`
* the assigned work falls within the active role's responsibilities
* the required inputs are available

When these conditions are satisfied, no additional user instruction is required. The role should begin work automatically in accordance with `role-lifecycle.md`.

A role must not begin project work when:

* it does not match `Next Role`
* `Human Intervention Required` is `Yes`
* required inputs are missing
* the required action exceeds the role's authority

In those cases, the role must stop and report the reason rather than making assumptions or performing work outside its responsibilities.

Loading a role does not independently authorise arbitrary work. Automatic execution is authorised only by the current state recorded in `project-state.md`.

Detailed activation, execution, handoff and state-update behaviour is defined by `role-lifecycle.md`.

---

# Primary Objective

Deliver reliable, maintainable software through disciplined execution while maximising value per token.

Success is measured by:

* predictable progress
* architectural consistency
* implementation quality
* low rework
* minimal unnecessary token consumption

---

# Guiding Principles

## Plan Before Building

Implementation must not begin until an approved implementation plan exists.

The implementation plan (`myplan.md`) is the authoritative description of the work to be completed.

---

## Design Before Coding

User-facing functionality must have approved UI designs before implementation begins.

Implementation must faithfully follow those designs.

UI design decisions belong to the UI Designer.

---

## Build One Phase At A Time

Only one implementation phase may be active.

Do not partially implement multiple phases simultaneously.

Complete the current phase before beginning the next.

---

## Keep Phases Small

Implementation phases should be independently implementable and independently testable.

Oversized phases significantly increase:

* implementation complexity
* debugging effort
* review effort
* token consumption

If a phase would reasonably require its own implementation plan or repeated implementation/debug cycles, it should be divided into smaller phases before implementation begins.

---

## Keep Architecture Stable

Implementation must remain faithful to the approved architecture.

Do not redesign:

* system architecture
* public interfaces
* component responsibilities

Architectural decisions belong to the Architect.

---

## Keep UI Stable

Implementation must remain faithful to approved UI designs.

Do not redesign:

* layouts
* navigation
* workflows
* interactions

Visual design decisions belong to the UI Designer.

---

# Engineering Philosophy

Prefer the simplest solution that completely satisfies the approved requirements.

Avoid unnecessary:

* abstraction
* configuration
* indirection
* design patterns
* layers
* future-proofing

Do not optimise for hypothetical future requirements.

Optimise for:

* correctness
* readability
* maintainability

---

# Modification Policy

When modifying existing code:

* preserve existing behaviour unless instructed otherwise
* minimise the scope of changes
* avoid unrelated refactoring
* avoid unnecessary file modifications

Every code change should have a clearly defined purpose.

---

# Testing Policy

Every implementation change must be validated.

The implementation workflow is:

```text
Implement

↓

Test

↓

Debug (if required)

↓

Re-test

↓

Review
```

No implementation proceeds to review until the latest implementation has passed testing.

---

# Review Policy

Code review is a quality gate.

The default outcome should be approval.

Review should request changes only when they materially improve:

* correctness
* security
* maintainability
* performance
* architectural compliance

Do not request changes based solely on:

* personal coding preferences
* stylistic differences
* speculative future requirements
* unnecessary abstraction
* preferred design patterns

The objective is reliable software, not theoretical perfection.

---

# Project Artefacts

The following artefacts are authoritative.

| Artefact       | Owner         |
| -------------- | ------------- |
| Requirements   | User          |
| myplan.md      | Architect     |
| UI Mockups     | UI Designer   |
| Source Code    | Implementer   |
| QA Findings    | Tester        |
| Debug Reports  | Debugger      |
| Review Reports | Reviewer      |
| Git History    | Git Assistant |

Do not modify artefacts owned by another role unless explicitly instructed.

---

# Documentation Standards

All project documentation should be:

* concise
* technically accurate
* evidence based
* actionable

Avoid unnecessary narrative.

Avoid documenting speculative work.

---

# Token Efficiency

Every activity should maximise value per token.

Prefer:

* focused implementation
* targeted debugging
* concise documentation
* minimal context
* small implementation phases

Avoid repeated implementation cycles caused by oversized phases.

Avoid unnecessary review cycles.

---

# Decision Hierarchy

When guidance conflicts, follow this order:

1. Explicit user instruction.
2. Current workflow state (`project-state.md`) for activation, current phase and handoff.
3. Shared role lifecycle (`role-lifecycle.md`) for execution behaviour.
4. Current role definition for specialist responsibilities and authority.
5. Approved implementation plan (`myplan.md`).
6. Approved UI designs.
7. This document for project governance and engineering principles.

`project-state.md` determines **what is active now**; it does not override approved requirements, architecture, designs, or role boundaries.

If uncertainty remains, or resolving a conflict requires a product, design or architectural decision, require human intervention rather than making assumptions.

---

# Success Criteria

The project is successful when:

* architecture remains consistent
* implementation follows the approved plan
* UI matches the approved design
* every phase is tested
* reviewed code is committed
* unnecessary implementation cycles are avoided

---

# Project Philosophy

Reliable software delivered today is more valuable than theoretically perfect software delivered later.

Optimise for disciplined execution, predictable progress and practical engineering rather than unnecessary sophistication.
