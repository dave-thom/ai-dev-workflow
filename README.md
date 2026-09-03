# AI Platform v2.0

Version: 2.0

---

# Purpose

AI Platform v2.0 defines a structured multi-model software development workflow designed to maximise implementation quality while minimising unnecessary token consumption.

The platform separates:

* Project governance
* Universal role behaviour
* Specialist role expertise

This separation allows every role to remain focused on its area of responsibility while following a common execution model.

---

# Directory Structure

```
.ai-platform/

role-lifecycle.md

prompts/
    role-architect.md
    role-ui-designer.md
    role-implementer.md
    role-tester.md
    role-debugger.md
    role-reviewer.md
    role-git.md

templates/
    CLAUDE.md
```

Each software project should contain:

```
project/

.git/
CLAUDE.md
myplan.md

docs/
    ui/
    qa/
    debug/
    reviews/

src/
...
```

---

# AI-Run Orchestrator

The `ai-run` orchestrator automates workflow execution based on `project-state.md`.

## Commands

* `ai-next` - Resolve next role and optionally execute it
* `ai-run-phase` - Repeat `ai-next` until the active phase changes
* `ai-run` - Repeat `ai-next` unconditionally across phases

## Configuration

Configuration is stored in `config/ai-run.json`:

```json
{
  "kickoff_prompt": "Begin the workflow defined by project-state.md.",
  "roles": {
    "implementer": { "command": ["ai-role", "opencode", "implementer", "-m", "openrouter/deepseek/deepseek-v3.2"] },
    "senior_implementer": { "command": ["ai-role", "opencode", "implementer", "-m", "openrouter/deepseek/deepseek-v4-pro"] },
    "senior_debugger": { "command": ["ai-role", "opencode", "debugger", "-m", "openrouter/deepseek/deepseek-v4-pro"] },
    "git": { "command": ["ai-role", "opencode", "git", "-m", "openrouter/deepseek/deepseek-v4-flash"] },
    "tester": { "command": ["ai-role", "claude", "tester", "--model", "sonnet", "--permission-mode", "auto"] },
    "reviewer": { "command": ["ai-role", "claude", "reviewer", "--model", "sonnet", "--permission-mode", "auto"] },
    "designer": { "command": ["ai-role", "claude", "designer", "--model", "sonnet", "--permission-mode", "auto"] }
  },
  "limits": {
    "senior_debugger_max": 3,
    "designer_max": 2,
    "phase_max_executions": 15
  }
}
```

## Runtime Files

* `.ai-run-state.json` - Tracks execution counters per phase
* `.ai-run.log` - Logs orchestration events

Both files must be git-ignored.

## Exit Codes

* `0` - Transition completed, or loop finished normally
* `2` - Stopped, human action required (escalation, limits, Architect, no progress)
* `3` - Runtime failure (non-zero child exit)
* `4` - Invalid or unparseable workflow state / configuration

## Runner Override

Create `.ai-run.json` in your project directory to override runners:

```json
{
  "roles": {
    "reviewer": { "command": ["custom-reviewer-script"] }
  },
  "limits": {
    "phase_max_executions": 20 
  }
}
```

---

# Workflow

The standard development workflow is:

```
Architect

↓

UI Designer

↓

Implementer

↓

Tester

↓

PASS

↓

Reviewer

↓

Git Assistant
```

If testing fails:

```
Implementer

↓

Tester

↓

FAIL

↓

Debugger

↓

Tester

↓

PASS

↓

Reviewer
```

---

# Escalation

Debugger:

Every debugger request is routed to the senior debugger runner (DeepSeek V4 Pro). The ordinary debugger tier is retired.

Maximum 3 debugger executions per phase.

---

# Responsibilities

Architect

Produces:

* myplan.md

UI Designer

Produces:

* UI mockups
* Phase UI specifications

Implementer

Produces:

* Working implementation

Tester

Produces:

* QA findings

Debugger

Produces:

* Debug report

Reviewer

Produces:

* Review report

Git Assistant

Produces:

* Commit
* Commit message

---

# Guiding Principles

* Architecture before implementation.
* UI before implementation.
* One implementation phase at a time.
* Small independently testable phases.
* Simple solutions preferred.
* Quality through iteration.
* No speculative engineering.
* Minimise unnecessary token usage.

---

# Governance

Every project contains:

* CLAUDE.md
* myplan.md

Every role follows:

* role-lifecycle.md

Every role defines only specialist expertise.

---

# Philosophy

Reliable software delivered today is more valuable than theoretically perfect software delivered later.

Optimise for:

* predictable progress
* disciplined execution
* architectural consistency
* token efficiency
* implementation quality
