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

DeepSeek V3.2

↓

DeepSeek R1

only when V3.2 cannot make further progress.

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
