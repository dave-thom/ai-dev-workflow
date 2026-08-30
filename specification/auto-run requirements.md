# AI Platform v2.0 — `ai-run` Workflow Orchestrator Requirements

## 1. Purpose

`ai-run` is a lightweight local workflow orchestrator for the existing AI Platform v2.0 development process.

Its purpose is to remove repetitive manual role invocation while preserving the existing role architecture, model/runtime separation, project-state model and human escalation points.

`ai-run` does not replace the existing AI roles, runtimes or workflow documents.

It coordinates them.

The primary objective is:

> Automate the routine development path while stopping safely whenever the workflow becomes ambiguous, exceptional or repeatedly unsuccessful.

---

# 2. Design Principles

`ai-run` must follow the existing AI Platform v2.0 principles:

- simple solutions
- deterministic behaviour
- minimal new infrastructure
- low coupling between roles
- low token overhead
- one authoritative source for each kind of information
- human intervention for architecture, design or genuinely ambiguous decisions
- fail closed rather than attempting speculative recovery

The orchestrator itself must contain no AI reasoning.

It must not infer what an agent probably intended.

It must operate from explicit workflow state and deterministic routing rules.

---

# 3. Existing Components

The orchestrator builds on the existing platform:

```text
role-lifecycle.md
role-*.md
CLAUDE.md
ai-role
project-state.md
myplan.md
current execution reports
shell/runtime configuration
```

The existing roles remain responsible for performing development work.

The existing runtimes remain responsible for executing models.

`project-state.md` remains the authoritative source of current workflow state.

---

# 4. Orchestrator Responsibilities

`ai-run` is responsible for:

- reading `project-state.md`
- determining which logical role is required next
- resolving that logical role to the appropriate concrete runner/model tier
- launching the role
- waiting for the role to complete
- validating that the workflow state has advanced
- recording orchestration-level execution counters
- enforcing retry and escalation limits
- continuing to the next role when safe
- stopping when human intervention is required
- stopping when workflow invariants are violated

`ai-run` is not responsible for:

- implementation
- debugging
- testing
- review
- architectural reasoning
- design reasoning
- interpreting QA findings
- deciding how defects should be fixed
- deciding whether requirements should change
- Git implementation details beyond validating workflow progress

Those responsibilities remain with the existing roles.

---

# 5. Logical Roles vs Concrete Runners

`project-state.md` records logical roles.

For example:

```text
Next Role: Implementer
Next Role: Tester
Next Role: Debugger
Next Role: Reviewer
Next Role: Git Assistant
Next Role: Architect
```

`ai-run` may resolve a logical role to different execution tiers depending on the current phase history.

For example:

```text
Implementer
    → o-dev
or
    → o-sdev
```

and:

```text
Debugger
    → o-debug
or
    → o-sdebug
```

`project-state.md` should not need to know whether the ordinary or senior implementation tier is selected.

That is orchestration policy.

---

# 6. Default Workflow

The expected normal path is:

```text
o-dev
  ↓
c-test
  ↓ FAIL
o-debug
  ↓
c-test
  ↓ FAIL
o-sdebug
  ↓
c-test
  ↓ PASS
c-review
  ↓ APPROVE
o-git
  ↓
o-dev for the next phase
```

The exact path may vary according to `project-state.md`.

---

# 7. Implementer Routing Rule

The ordinary Implementer may be invoked no more than once during a given phase.

The first request for the logical role:

```text
Implementer
```

during a new phase resolves to:

```text
o-dev
```

Once `o-dev` has been invoked for that phase, it must never be invoked again during the same phase.

Any subsequent requirement for an Implementer-class role during that phase resolves to:

```text
o-sdev
```

This applies regardless of why further implementation is required.

Examples include:

- Tester identifies substantial implementation rework
- Reviewer requests changes
- a debugging cycle determines the issue requires reimplementation rather than defect correction
- any later workflow transition sets `Next Role: Implementer`

Therefore:

```text
First Implementer invocation in phase
    → o-dev

All subsequent Implementer invocations in same phase
    → o-sdev
```

---

# 8. Debugger Routing Rule

The first request for:

```text
Next Role: Debugger
```

during a phase resolves to:

```text
o-debug
```

Any subsequent Debugger request during the same phase resolves to:

```text
o-sdebug
```

The ordinary debugger may therefore run at most once per phase.

The senior debugger may run at most three times per phase by default.

This allows for the observed pattern where resolving one blocking defect exposes another defect that could not previously be reached.

The maximum default debug sequence is therefore:

```text
o-debug
c-test
o-sdebug
c-test
o-sdebug
c-test
o-sdebug
c-test
```

If QA still requires debugging after the third senior-debugger invocation:

```text
STOP
```

Human investigation is required.

---

# 9. Tester Routing

The logical role:

```text
Tester
```

resolves directly to:

```text
c-test
```

Tester may run multiple times within the limits imposed by the overall phase circuit breaker.

A Tester invocation must not automatically cause another Tester invocation unless `project-state.md` genuinely advances through another role first.

Unexpected Tester-to-Tester self-transitions should be treated as non-progress or invalid state.

---

# 10. Reviewer Routing

The logical role:

```text
Reviewer
```

resolves directly to:

```text
c-review
```

If Reviewer approves the phase, the expected next role is:

```text
Git Assistant
```

If Reviewer requests implementation changes and `project-state.md` sets:

```text
Next Role: Implementer
```

the normal Implementer routing rule applies.

Because `o-dev` has already been used for the phase, this will resolve automatically to:

```text
o-sdev
```

No reviewer-specific implementation routing rule is required.

---

# 11. Git Routing

The logical role:

```text
Git Assistant
```

resolves directly to:

```text
o-git
```

The Git Assistant remains responsible for:

- final Git hygiene
- rebasing where appropriate
- squashing provisional commits where appropriate
- resolving routine conflicts within its authority
- merging the approved phase
- pushing final changes
- branch cleanup
- final repository state

If the Git Assistant cannot complete its task safely because of:

- unexpected repository state
- conflict requiring judgement
- repository corruption
- deployment/release ambiguity
- any condition requiring user decision

the workflow must stop.

`ai-run` must not automatically retry Git indefinitely.

---

# 12. Architect Rule

The Architect must never be launched automatically by `ai-run`.

If:

```text
Next Role: Architect
```

the workflow must stop immediately.

The runner should report:

- active phase
- current state
- reason for stopping
- relevant current report/document pointers

The user may then investigate manually and invoke the Architect as appropriate.

---

# 13. Human Intervention Rule

If `project-state.md` indicates:

```text
Human Intervention Required: Yes
```

the workflow must stop immediately.

The orchestrator must not attempt to interpret or resolve the issue.

The user must regain control.

The same applies when a role reports that:

- architecture must change
- requirements are ambiguous
- a design decision is required
- user input is required
- required credentials or external actions are unavailable
- the current role lacks authority to continue

---

# 14. Single-Step Runner

The core execution primitive should be:

```bash
ai-next
```

`ai-next` performs exactly one workflow transition.

It must:

1. read `project-state.md`
2. validate current state
3. determine the logical `Next Role`
4. resolve the concrete runner
5. enforce role invocation limits
6. launch the role
7. wait for completion
8. re-read `project-state.md`
9. validate that meaningful workflow progress occurred
10. update orchestration runtime state
11. return control

`ai-next` must never execute a second role automatically.

---

# 15. Dry-Run Mode

`ai-next` must support:

```bash
ai-next --dry-run
```

Dry-run mode must not launch an AI runtime.

It should report at minimum:

```text
Project
Active Phase
Current Status
Logical Next Role
Resolved Runner
Current phase counters
Command that would be executed
Reason for any escalation decision
```

Example:

```text
Project: Family School Assistant
Phase: 13
Next logical role: Debugger

Debugger runs this phase:
  normal: 1
  senior: 1

Resolved runner:
  o-sdebug

No command executed.
```

Dry-run mode should be used to validate routing before enabling full automation.

---

# 16. Continuous Phase Runner

A second command should be provided:

```bash
ai-run-phase
```

It repeatedly executes the equivalent of `ai-next` until one of the following occurs:

- the current phase is successfully completed
- the active phase changes
- human intervention is required
- Architect is required
- a guardrail is reached
- a runtime fails unexpectedly
- workflow state becomes invalid or ambiguous

When the phase completes successfully, `ai-run-phase` exits rather than automatically beginning the next phase.

---

# 17. Continuous Project Runner

The full command is:

```bash
ai-run
```

`ai-run` repeatedly executes workflow transitions across phases.

When Git successfully closes one phase and `project-state.md` advances to the next phase with:

```text
Next Role: Implementer
```

the phase counters reset and the next phase begins automatically.

`ai-run` continues until:

- the active plan is complete
- workflow reaches an idle/awaiting-work state
- Architect is required
- human intervention is required
- a guardrail is triggered
- an unexpected failure occurs

---

# 18. Runtime State

Orchestration counters must not be stored in `project-state.md`.

They are runtime metadata, not project workflow state.

A separate file should be used, for example:

```text
.ai-run-state.json
```

Possible structure:

```json
{
  "phase": "Phase 13",
  "implementer_runs": 1,
  "senior_implementer_runs": 0,
  "tester_runs": 3,
  "debugger_runs": 1,
  "senior_debugger_runs": 2,
  "reviewer_runs": 0,
  "git_runs": 0,
  "total_runs": 7
}
```

The implementation may refine the exact schema.

The important principle is:

> `project-state.md` records workflow state.  
> `.ai-run-state.json` records orchestrator execution history required to enforce runtime policy.

---

# 19. Phase Detection

When the value of:

```text
Active Phase
```

changes, the orchestrator should treat this as a new phase.

Phase-specific counters must reset.

The orchestrator must not infer phase changes from Git history, report filenames or old documentation.

`project-state.md` is authoritative.

---

# 20. Global Phase Circuit Breaker

In addition to role-specific limits, each phase must have a hard maximum number of AI-role executions.

Initial default:

```text
Maximum role executions per phase: 12
```

This accommodates the maximum normal debug path:

```text
o-dev
c-test
o-debug
c-test
o-sdebug
c-test
o-sdebug
c-test
o-sdebug
c-test
c-review
o-git
```

If a thirteenth role execution would be required:

```text
STOP
```

The user must investigate.

This protects against unforeseen loops that individual role counters do not catch.

---

# 21. Progress Validation

Before launching a role, `ai-run` must record the relevant current state.

At minimum:

```text
Active Phase
Status
Next Role
Human Intervention Required
Git branch
current QA state if present
current Review state if present
```

After the role exits, the orchestrator must re-read `project-state.md`.

Meaningful workflow progress must have occurred.

If the role exits but the relevant workflow state is unchanged:

```text
STOP
```

The orchestrator must not simply invoke the same role again.

Possible stop message:

```text
Automation stopped.

Role completed without advancing project-state.md.

Phase: 13
Role: Tester
Next Role remains: Tester

Human investigation required.
```

---

# 22. Invalid Transition Handling

The orchestrator must stop on:

- unknown `Next Role`
- missing `project-state.md`
- unparseable required fields
- missing active phase where one is required
- contradictory workflow state
- current role returning itself as next role without an explicitly supported self-transition
- execution limits exceeded
- required runner configuration missing
- runtime process exits unexpectedly
- role reports completion without advancing state

The orchestrator must not attempt to repair malformed workflow state automatically.

---

# 23. Runtime Failure Handling

If a launched runtime exits with a non-success exit code or otherwise fails to complete normally:

```text
STOP
```

The orchestrator should report:

- phase
- logical role
- concrete runner
- exit status
- current `project-state.md` state

Automatic retry of failed runtime invocations should not be part of the first implementation.

This prevents infrastructure errors from becoming execution loops.

---

# 24. Role Command Configuration

Automation must not depend on shell alias expansion.

Interactive aliases such as:

```text
o-dev
o-debug
o-sdebug
o-sdev
c-test
c-review
o-git
```

may remain available for manual use.

The orchestrator should use explicit command configuration.

For example:

```yaml
roles:
  implementer:
    command: [...]

  senior_implementer:
    command: [...]

  tester:
    command: [...]

  debugger:
    command: [...]

  senior_debugger:
    command: [...]

  reviewer:
    command: [...]

  git:
    command: [...]
```

The exact format may be chosen during implementation.

Role, model and runtime must remain conceptually separate.

---

# 25. Claude Invocation

Claude Code roles used by automation should run non-interactively.

The expected pattern is equivalent to:

```bash
claude -p \
  --permission-mode auto \
  ... \
  "Begin the workflow defined by project-state.md."
```

The exact command should continue to use the existing `ai-role` prompt-composition mechanism where practical.

Claude must receive an initial prompt because loading the interactive REPL alone does not create an execution turn.

---

# 26. OpenCode Invocation

OpenCode roles should use their existing non-interactive/build execution behaviour.

The existing `ai-role` wrapper should continue to provide:

```text
role-lifecycle.md
+
role-specific prompt
```

The orchestrator should not duplicate role prompts.

---

# 27. Git Validation

Where a code-changing role hands work to Tester, existing role contracts require that changes are committed and pushed.

`ai-run` should mechanically validate the handoff where practical.

For example:

- active branch exists
- working tree is clean
- branch has an upstream
- local committed state is available remotely

If `project-state.md` claims:

```text
Next Role: Tester
```

but required code remains uncommitted or unpushed:

```text
STOP
```

This is a role-contract violation.

The orchestrator should not silently commit the work itself.

---

# 28. Logging

The orchestrator should maintain a concise execution log, for example:

```text
.ai-run.log
```

Example:

```text
13:04:11 Phase 13 → Implementer → o-dev
13:18:42 completed → Tester
13:18:42 Phase 13 → Tester → c-test
13:27:01 completed → Debugger
13:27:01 Phase 13 → Debugger → o-debug
13:36:18 completed → Tester
```

The log should record orchestration events only.

It should not duplicate:

- QA reports
- debug reports
- review reports
- agent reasoning
- implementation summaries

---

# 29. Interruption and Restart

The runtime-state file should make it possible to restart `ai-run` without losing phase counters.

On startup, the runner must compare:

```text
.ai-run-state.json
```

with:

```text
project-state.md
```

If the recorded phase differs from the current active phase, initialise new phase counters.

If state is inconsistent or cannot be safely reconciled:

```text
STOP
```

Do not guess.

---

# 30. Manual Operation Must Remain Possible

Automation must not remove the existing manual workflow.

The user must continue to be able to run:

```text
o-dev
c-test
o-debug
o-sdebug
o-sdev
c-review
o-git
```

independently.

`ai-run` is an additional execution mode, not a replacement for direct role invocation.

---

# 31. Initial Commands

The first implementation should provide:

```bash
ai-next
ai-next --dry-run
ai-run-phase
ai-run
```

No graphical interface is required.

---

# 32. Out of Scope for Initial Version

Do not initially implement:

- GUI
- web dashboard
- daemon/service
- cloud orchestration
- notifications
- Slack/email alerts
- AI-based workflow decisions
- automatic Architect execution
- automatic design decisions
- automatic recovery from malformed project state
- arbitrary workflow-definition DSL
- dynamic model selection
- cost optimisation engine
- parallel role execution
- multi-project orchestration

These may be considered later only if an observed need emerges.

---

# 33. Acceptance Criteria

The first implementation is complete when:

1. `ai-next --dry-run` correctly resolves every supported logical role without executing it.
2. First Implementer invocation in a phase resolves to ordinary Implementer.
3. Every later Implementer invocation in the same phase resolves to Senior Developer.
4. First Debugger invocation resolves to ordinary Debugger.
5. Subsequent Debugger invocations resolve to Senior Debugger.
6. Senior Debugger cannot run more than three times per phase.
7. Architect state always stops automation.
8. Human-intervention state always stops automation.
9. Unknown or malformed state always stops automation.
10. A role that does not advance workflow state causes automation to stop.
11. Code-changing handoffs to Tester can be rejected when required changes are not committed/pushed.
12. `ai-run-phase` can complete one normal phase automatically.
13. `ai-run` can continue from one completed phase into the next.
14. Phase counters reset when `Active Phase` changes.
15. The 12-role phase circuit breaker prevents unbounded execution.
16. Runtime failures stop automation rather than triggering uncontrolled retries.
17. Manual role invocation remains unaffected.
18. `project-state.md` remains free of orchestrator counters or execution history.

---

# 34. Success Measure

The orchestrator is successful when the normal development workflow can proceed unattended through routine implementation, testing, debugging, review and Git integration, while reliably returning control to the user whenever continued autonomous execution would be unsafe, ambiguous or repeatedly unsuccessful.

The optimisation target remains:

> total time and cost per successfully completed phase

rather than maximum autonomy.