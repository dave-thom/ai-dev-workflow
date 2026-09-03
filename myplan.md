# Implementation Plan — `ai-run` Workflow Orchestrator

Version: 1.3

Source specification: `specification/auto-run requirements.md`

---

# 1. Specification Validation Outcome

The specification was validated against the actual repository, role contracts, shell
configuration and installed runtimes before planning. Findings and their resolutions:

| # | Finding | Resolution |
|---|---------|------------|
| 1 | §26 states OpenCode already has non-interactive behaviour. It does not. `bin/ai-role` runs `opencode --prompt` (TUI) and `claude` without `-p`. Both are interactive. | `ai-role` gains a batch mode (Phase 1). |
| 2 | `c-review` referenced in §6/§10/§30 does not exist. The alias is `c-rev`. | Aliases are not used by automation (§24). Runner commands are defined explicitly in config. |
| 3 | §5 omits UI Designer, yet `prompts/role-designer.md`, the `c-design` alias and the `UI Specification` state field exist. | **User decision:** `UI Designer` is a supported logical role resolving to the Claude designer runner. |
| 4 | §20's limit of 12 exactly equals the maximum debug path, making the §10 Reviewer-rework path unreachable in any phase that debugged. | **User decision:** default raised to 15, configurable. |
| 5 | No role owns advancing `Active Phase`; §17 and acceptance criteria 13–14 depend on it. | **User decision:** `prompts/role-git.md` gains an explicit phase-advance responsibility, plus an orchestrator guardrail. |
| 6 | §13's non-`project-state` triggers ("role reports architecture must change") require reading agent output, which is inference and forbidden by §2. | Detection is via `Human Intervention Required: Yes` only. Agent output is never parsed. |
| 7 | `.ai-run-state.json` and `.ai-run.log` live in the project directory and would dirty the working tree, failing the orchestrator's own §27 clean-tree check. | Startup guard requires both paths to be git-ignored. |
| 8 | `Status` has no defined vocabulary, so §17's "plan complete / idle" stop condition is not deterministic. | Completion and idle are detected from `Next Role` (`Architect`, `None`, unknown) and `Human Intervention Required`, never from `Status` text. |
| 9 | Acceptance criteria 12–13 cannot be tested without live paid model runs. | Runner commands are configurable, so a stub-runner fixture exercises both offline (Phases 8a–8c). |

---

# 2. Architecture Overview

`ai-run` is a single Python package invoked through three thin executables on `PATH`.

```text
$AI_PLATFORM/
    airun/                  orchestrator package (stdlib only)
        __init__.py
        __main__.py         argparse entry point
        state.py            project-state.md parsing
        config.py           runner and limit configuration
        runtime.py          .ai-run-state.json counters
        routing.py          logical role -> concrete runner
        guards.py           git handoff and ignore-file validation
        launcher.py         subprocess execution
        logbook.py          .ai-run.log
        errors.py           Stop / exit-code taxonomy
    bin/
        ai-role             existing launcher (gains batch mode)
        ai-next             exec python3 -m airun next "$@"
        ai-run-phase        exec python3 -m airun run-phase "$@"
        ai-run              exec python3 -m airun run "$@"
    config/
        ai-run.json         default runner and limit configuration
```

Data flow for one transition:

```text
project-state.md ──> state.py ──┐
.ai-run-state.json ──> runtime.py ──┤
config/ai-run.json ──> config.py ──┴──> routing.py ──> guards.py ──> launcher.py
                                                                          │
                                                     re-read project-state.md
                                                                          │
                                                    progress validation ──> runtime.py + logbook.py
```

## Technology Decision

Implementation language: **Python 3, standard library only** (target 3.9, the system
interpreter at `/usr/bin/python3`).

Rationale: the orchestrator must parse Markdown fields, read and write JSON runtime
state, read JSON configuration, manage subprocesses and exit codes, and be unit
testable without live model runs. Bash would require `jq` (new infrastructure,
contrary to §2) and offers no practical way to unit test routing rules. No third-party
packages are used, so there is no virtualenv, lockfile or install step.

Configuration format is JSON rather than the YAML sketched in §24; §24 explicitly
permits the format to be chosen during implementation, and JSON removes a dependency.

## Working Directory Rule

All commands operate on the current working directory. `project-state.md`,
`.ai-run-state.json` and `.ai-run.log` are resolved relative to it. The orchestrator
never searches parent directories and never reads `$AI_PLATFORM/project-state.md`
unless that is the working directory.

---

# 3. Component Responsibilities

## `state.py`

Parses `project-state.md` into an immutable snapshot. Fields extracted:

```text
Project / Name
Workflow / Status
Workflow / Active Phase
Workflow / Current Role
Workflow / Next Role
Workflow / Next Action
Git / Branch
Execution / Implementation
Execution / QA
Execution / Review
Escalation / Human Intervention Required
Escalation / Reason
```

Parsing rules: a field is `^\s*<Label>:\s*(.*)$` within its section. Values are
stripped. A missing required field is a fatal parse error. Never repairs, never
infers, never writes.

Interface:

```python
class ProjectState(NamedTuple):
    name: str
    status: str
    active_phase: str
    current_role: str
    next_role: str
    next_action: str
    branch: str
    implementation: str
    qa: str
    review: str
    human_intervention: bool
    reason: str
    raw: dict          # every parsed label -> value

def read_project_state(path: str) -> ProjectState   # raises InvalidStateError
def progress_snapshot(s: ProjectState) -> dict      # §21 fields only
```

## `config.py`

Loads `$AI_PLATFORM/config/ai-run.json`, then shallow-merges an optional project-local
`.ai-run.json` over it (`roles` merged per key, `limits` merged per key). Validates
that every runner referenced by routing has a non-empty `command` list.

Schema:

```json
{
  "kickoff_prompt": "Begin the workflow defined by project-state.md.",
  "roles": {
    "implementer":        { "command": ["ai-role", "opencode", "implementer", "-m", "openrouter/deepseek/deepseek-v3.2"] },
    "senior_implementer": { "command": ["ai-role", "opencode", "implementer", "-m", "openrouter/deepseek/deepseek-v4-pro"] },
    "debugger":           { "command": ["ai-role", "opencode", "debugger",    "-m", "openrouter/deepseek/deepseek-v3.2"] },
    "senior_debugger":    { "command": ["ai-role", "opencode", "debugger",    "-m", "openrouter/deepseek/deepseek-v4-pro"] },
    "git":                { "command": ["ai-role", "opencode", "git",         "-m", "openrouter/deepseek/deepseek-v4-flash"] },
    "tester":             { "command": ["ai-role", "claude", "tester",   "--model", "sonnet", "--permission-mode", "auto"] },
    "reviewer":           { "command": ["ai-role", "claude", "reviewer", "--model", "sonnet", "--permission-mode", "auto"] },
    "designer":           { "command": ["ai-role", "claude", "designer", "--model", "sonnet", "--permission-mode", "auto"] }
  },
  "limits": {
    "senior_debugger_max": 3,
    "designer_max": 2,
    "phase_max_executions": 15
  }
}
```

The kickoff prompt is appended as the final argument of every launch, and
`AI_ROLE_BATCH=1` is set in the child environment.

## `runtime.py`

Owns `.ai-run-state.json`:

```json
{
  "schema": 1,
  "phase": "Phase 13",
  "counters": {
    "implementer": 1, "senior_implementer": 0, "designer": 0,
    "tester": 3, "debugger": 1, "senior_debugger": 2,
    "reviewer": 0, "git": 0
  },
  "total_runs": 7
}
```

Reconciliation on load (§29):

* file absent → initialise counters at zero for the current `Active Phase`
* `phase` equals current `Active Phase` → retain counters
* `phase` differs → reset all counters to zero and set `phase` (§19)
* unparseable JSON, wrong `schema`, missing `counters`, negative or non-integer
  counter, or `total_runs` less than the sum of counters → `StopRequired`

Counters are incremented only after a launch is attempted, and persisted before
progress validation so an interrupted run cannot under-count.

## `routing.py`

Pure function, no I/O. Normalises `Next Role` by lowercasing, stripping and collapsing
internal whitespace, then applies:

| Normalised `Next Role` | Resolution |
|---|---|
| `architect` | STOP — Architect must never be launched (§12) |
| `ui designer`, `designer` | `designer` runner, while `designer` count < `designer_max` |
| `implementer` | `implementer` if `implementer` count == 0, otherwise `senior_implementer` (§7) |
| `tester` | `tester` (§9) |
| `debugger` | `debugger` if `debugger` count == 0, otherwise `senior_debugger` (§8) |
| `reviewer` | `reviewer` (§10) |
| `git assistant`, `git` | `git` (§11) |
| `none`, empty | STOP — workflow idle |
| anything else | STOP — unknown role (§22) |

Limit checks applied in this order, each producing a distinct stop reason:

1. `Human Intervention Required: Yes` → STOP (§13)
2. `Next Role: Architect` → STOP (§12)
3. `Active Phase` absent or `None` while a role other than Architect is requested → STOP (§22)
4. unknown or idle `Next Role` → STOP (§22)
5. `total_runs >= phase_max_executions` → STOP (§20)
6. resolution is `senior_debugger` and `senior_debugger` count >= `senior_debugger_max` → STOP (§8)
7. resolution is `designer` and `designer` count >= `designer_max` → STOP

Interface:

```python
class Decision(NamedTuple):
    action: str          # "launch" | "stop"
    logical_role: str
    runner: str          # "" when stopping
    reason: str
    rule: str            # spec section reference, e.g. "§8"

def resolve(state: ProjectState, counters: dict, limits: dict) -> Decision
```

## `guards.py`

Two independent guards.

**Ignore guard** (runs at startup of every command, including dry-run): `.ai-run-state.json`
and `.ai-run.log` must be ignored by git in the working directory. Verified with
`git check-ignore -q <path>`. Failure stops with a message naming the two paths.
Skipped when the working directory is not a git repository.

**Git handoff guard** (§27, runs only when the resolved decision is `launch` and
`Next Role` is `Tester`):

1. working directory is a git repository
2. current branch equals `Git / Branch` in `project-state.md`
3. `git status --porcelain` is empty
4. an upstream exists: `git rev-parse --abbrev-ref --symbolic-full-name @{u}`
5. `git fetch <remote> <branch>` succeeds, then local `HEAD` equals the upstream commit

Any failure stops with a role-contract-violation message. The guard never commits,
stages, pushes or otherwise mutates the repository.

## `launcher.py`

Builds `command + [kickoff_prompt]`, sets `AI_ROLE_BATCH=1` in a copy of the
environment, and runs it with `subprocess.run` in the working directory, inheriting
stdin, stdout and stderr so role output remains visible. No timeout in this version.
A non-zero exit code stops automation with no retry (§23).

## `logbook.py`

Appends single lines to `.ai-run.log`:

```text
13:04:11 Phase 13 | launch  | Implementer -> implementer (o-dev tier)
13:18:42 Phase 13 | done    | Implementer exit=0 next=Tester
13:18:42 Phase 13 | stop    | §8 senior debugger limit reached
```

Orchestration events only. Never role output, findings or reasoning.

## `__main__.py`

Subcommands `next`, `run-phase`, `run`. `next` accepts `--dry-run`.

Exit codes:

| Code | Meaning |
|---|---|
| 0 | transition completed, or loop finished normally |
| 2 | stopped, human action required (escalation, limits, Architect, no progress) |
| 3 | runtime failure (non-zero child exit) |
| 4 | invalid or unparseable workflow state / configuration |

## Progress Validation (§21)

After the child exits, `project-state.md` is re-read. Progress occurred if **any** of:

* `Human Intervention Required` changed to `Yes`
* `Active Phase` changed
* `Next Role` differs from the logical role just invoked

Otherwise automation stops with exit code 2. This single rule also satisfies §9
(a Tester-to-Tester self-transition is not progress) and §22 (a role returning itself
as next role).

## Phase-Advance Guardrail

When the logical role just invoked was `Git Assistant` and the child exited zero:
if `Next Role` is `Implementer` but `Active Phase` is unchanged, stop with exit code 2
and the reason "Git Assistant did not advance Active Phase". This prevents the next
phase's first Implementer invocation from wrongly resolving to the senior tier.

## Loop Semantics

`ai-run-phase`: repeat `next` while the decision is `launch` and `Active Phase` is
unchanged from the value observed at loop start. Exit 0 when the phase completes
(`Active Phase` changes, or `Next Role` becomes `Architect`/`None`); propagate any
stop code otherwise.

`ai-run`: repeat `next` unconditionally until a stop. A change in `Active Phase` is
not a stop; counters reset via `runtime.py` and the loop continues (§17).

---

# 4. Implementation Phases

## Phase 1 — Platform Preparation

**Objective:** make non-interactive role execution and phase advancement possible
before any orchestrator code exists.

**Scope:**

* `bin/ai-role`: add batch mode, selected by `AI_ROLE_BATCH=1`.
  * claude: `claude -p --append-system-prompt "$COMBINED_PROMPT" "$@"`
  * opencode: split the final argument off as the message; run
    `opencode run --auto "${RUNTIME_ARGS[@]}" "$COMBINED_PROMPT\n\n$MESSAGE"`
  * Interactive behaviour when `AI_ROLE_BATCH` is unset must be byte-identical to today.
* `bin/ai-role`: add `AI_ROLE_DRYRUN=1`, which prints the fully resolved command it
  would `exec` (one argument per line) and exits 0 without launching a runtime.
* `tests/fixtures/ai-role-baseline/`: **before** modifying `bin/ai-role`, capture the
  exact argument vector today's script would `exec` for every alias form defined in
  `~/.zshrc` — `c-ta`, `c-design`, `c-test`, `c-rev`, `c-sdev`, `c-pdebug`, `o-dev`,
  `o-devr1`, `o-sdev`, `o-debug`, `o-sdebug`, `o-git`. Capture method: copy the
  unmodified script and replace its two `exec` lines with `printf '%s\n'`. One fixture
  file per alias form, committed as the regression baseline.
* `prompts/role-git.md`: add a Phase Advancement responsibility — after successful
  integration of an approved phase, set `Active Phase` to the next phase from
  `myplan.md` and `Next Role` to the role that phase requires; if `myplan.md` has no
  further phase, set `Next Role: Architect`.
* `.gitignore`: add `.ai-run-state.json` and `.ai-run.log`; mirror into
  `templates/` guidance.
* `config/ai-run.json`: create with the schema in §3.

**Acceptance criteria:**

1. `AI_ROLE_DRYRUN=1 AI_ROLE_BATCH=1 ai-role claude tester --model sonnet --permission-mode auto "Begin the workflow defined by project-state.md."` prints a command beginning `claude -p --append-system-prompt` and containing the kickoff prompt as the last argument; exit 0; no runtime launched.
2. The equivalent opencode invocation prints a command beginning `opencode run --auto`, containing `-m <model>`, with a single final message argument that contains both the role prompt text and the kickoff prompt.
3. With `AI_ROLE_BATCH` unset, `AI_ROLE_DRYRUN=1` output is **byte-identical** to the captured baseline for every alias form in `tests/fixtures/ai-role-baseline/`. This is the regression guarantee for the manual workflow (§30): any drift in prompt composition, argument order, flag set or whitespace fails the phase.
4. `ai-role` with an unknown runtime or missing role file still fails with the existing messages and non-zero exit.
5. `prompts/role-git.md` contains the phase-advance responsibility.
6. `git check-ignore -q .ai-run-state.json && git check-ignore -q .ai-run.log` succeeds in this repository.
7. `config/ai-run.json` parses as JSON and contains all eight runners plus the three limits.

**Deferred to later phases:** all orchestrator code.

## Phase 2 — Project State Parser

**Objective:** deterministic, read-only parsing of `project-state.md`.

**Scope:** `airun/__init__.py`, `airun/errors.py`, `airun/state.py`, and a fixture
directory `tests/fixtures/state/` containing valid, malformed and partial examples.

**Acceptance criteria:**

1. A copy of `templates/project-state.md` parses, yielding `next_role == "Architect"`, `active_phase == "None"`, `human_intervention is False`.
2. A fixture with `Human Intervention Required: Yes` yields `human_intervention is True`.
3. A fixture missing the `Next Role` field raises `InvalidStateError` naming the field.
4. A fixture with a duplicated `Next Role` in two sections raises `InvalidStateError`.
5. A non-existent path raises `InvalidStateError`.
6. Leading and trailing whitespace around values is stripped; internal spacing preserved.
7. `progress_snapshot` returns exactly the §21 fields.
8. `state.py` performs no writes and imports nothing outside the standard library.

**Deferred:** routing, counters, execution.

## Phase 3 — Configuration and Runtime State

**Objective:** load runner configuration and manage phase counters with safe
reconciliation.

**Scope:** `airun/config.py`, `airun/runtime.py`, fixtures under `tests/fixtures/runtime/`.

**Acceptance criteria:**

1. `load_config` reads `$AI_PLATFORM/config/ai-run.json` and returns all eight runners and three limits.
2. A project-local `.ai-run.json` overriding `limits.phase_max_executions` and one runner command produces a merged config with all other values unchanged.
3. A config whose runner has an empty or missing `command` raises `InvalidStateError`.
4. Missing `.ai-run-state.json` initialises all counters to zero with `phase` set to the current `Active Phase`.
5. A state file whose `phase` matches retains its counters.
6. A state file whose `phase` differs resets every counter to zero and `total_runs` to zero, and records the new phase.
7. Unparseable JSON, `schema != 1`, a missing `counters` key, a negative counter, or `total_runs` less than the sum of counters each raise `StopRequired` with a distinct reason.
8. `save` writes atomically (temporary file plus rename) and round-trips exactly.

**Deferred:** routing decisions, git guards, execution.

## Phase 4 — Routing Engine

**Objective:** implement every routing and limit rule as a pure function.

**Scope:** `airun/routing.py` and its unit tests.

**Acceptance criteria:**

1. `Next Role: Implementer` with `implementer == 0` resolves to runner `implementer`.
2. `Next Role: Implementer` with `implementer == 1` resolves to `senior_implementer`, and does so for every subsequent count.
3. `Next Role: Debugger` with `debugger == 0` resolves to `debugger`.
4. `Next Role: Debugger` with `debugger == 1` resolves to `senior_debugger`.
5. `senior_debugger == 3` with `Next Role: Debugger` stops with rule `§8`.
6. `Next Role: Architect` stops with rule `§12`, regardless of counters.
7. `Human Intervention Required: Yes` stops with rule `§13`, and is checked before role resolution so it stops even when `Next Role` is Architect or unknown.
8. `Next Role: Reviewer`, `Tester`, `Git Assistant`, `UI Designer` resolve to `reviewer`, `tester`, `git`, `designer`.
9. `Next Role: Designer` (without "UI") also resolves to `designer`.
10. `Next Role: Nonsense` stops with rule `§22`.
11. `Next Role: None` or empty stops as idle.
12. `total_runs == phase_max_executions` stops with rule `§20` before any role-specific limit is evaluated.
13. `Active Phase: None` with `Next Role: Implementer` stops with rule `§22`.
14. Role matching is case- and whitespace-insensitive (`next role: git   assistant` resolves to `git`).
15. `resolve` performs no file, subprocess or network access.

**Deferred:** git validation, launching, logging.

## Phase 5 — `ai-next --dry-run`

**Objective:** a working, non-executing command that satisfies the routing acceptance
criteria end to end.

**Scope:** `airun/__main__.py` (subcommand `next`, `--dry-run` only), `bin/ai-next`,
`airun/logbook.py`.

**Acceptance criteria:**

1. `bin/ai-next` is executable, sets `PYTHONPATH` to `$AI_PLATFORM`, and execs `python3 -m airun next "$@"`.
2. `ai-next --dry-run` prints, at minimum: Project, Active Phase, Status, logical Next Role, resolved runner, current phase counters, the exact command that would be executed, and the reason for any escalation decision (§15).
3. The printed command is the configured runner command plus the kickoff prompt as its final argument.
4. Dry-run launches no runtime: verified by pointing a runner at a script that writes a sentinel file and asserting the file is absent.
5. Dry-run writes no `.ai-run-state.json` and appends no `.ai-run.log` entry.
6. Dry-run against an Architect state prints the stop reason, active phase, current status and current deliverable pointers, and exits 2 (§12).
7. Dry-run against a malformed `project-state.md` exits 4.
8. Dry-run in a directory where `.ai-run-state.json` is not git-ignored exits 4 naming both runtime paths.
9. Exit code is 0 when the decision is `launch`.

**Deferred:** real execution, git handoff guard, loops.

## Phase 6 — Guards

**Objective:** enforce the code-handoff contract and the ignore-file precondition.

**Scope:** `airun/guards.py`, wired into the `next` command ahead of launching;
test fixtures using temporary local git repositories.

**Acceptance criteria:**

1. With `Next Role: Tester` and an uncommitted modification present, `ai-next --dry-run` stops with a role-contract violation and exits 2.
2. With `Next Role: Tester` and a committed but unpushed commit, it stops and exits 2.
3. With `Next Role: Tester`, a clean tree, an upstream, and local `HEAD` equal to upstream, it proceeds.
4. With `Next Role: Tester` and no upstream configured, it stops and exits 2.
5. With `Next Role: Tester` and the current branch differing from `Git / Branch`, it stops and exits 2.
6. The guard is not applied when `Next Role` is anything other than `Tester`.
7. No guard path ever runs `git add`, `git commit`, `git push`, `git checkout` or `git reset`; only `status`, `rev-parse`, `fetch`, `check-ignore` and `symbolic-ref` are used.
8. A working directory that is not a git repository stops with a clear message when `Next Role: Tester`, and does not stop the ignore guard.

**Deferred:** launching, loops.

## Phase 7 — Live Single-Step Execution

**Objective:** complete `ai-next` — launch, wait, validate progress, update counters, log.

**Scope:** `airun/launcher.py`, `next` without `--dry-run`, progress validation, the
phase-advance guardrail, runtime failure handling.

**Acceptance criteria:**

1. With a stub runner configured, `ai-next` launches it exactly once, waits for it to exit, and returns.
2. `AI_ROLE_BATCH=1` is present in the child environment; the parent environment is otherwise inherited.
3. The child's stdout and stderr appear on the parent's streams.
4. A stub that advances `Next Role` from `Implementer` to `Tester` causes exit 0, `implementer` counter 1, `total_runs` 1, and one launch plus one completion line in `.ai-run.log`.
5. A stub that exits 0 without changing `Next Role` causes exit 2 with a message naming the phase, the role and the unchanged `Next Role`; the counter is still incremented; no second launch occurs (§21).
6. A stub that exits non-zero causes exit 3 with a message reporting phase, logical role, runner, exit status and current state; no retry occurs (§23).
7. A stub that sets `Human Intervention Required: Yes` counts as progress and exits 0; the following `ai-next` exits 2.
8. A stub acting as Git Assistant that sets `Next Role: Implementer` without changing `Active Phase` causes exit 2 with the phase-advance guardrail message.
9. A stub acting as Git Assistant that sets `Next Role: Implementer` and advances `Active Phase` exits 0.
10. `ai-next` never launches a second role in one invocation (§14): verified by a stub that appends to a counter file.
11. Counters are persisted before progress validation, so a stop still records the execution.

**Deferred:** the two loop commands.

## Phase 8a — Loop Commands, Stub Harness and Documentation

**Delivered.** Verified by `docs/qa/phase-8-qa-report-3.md`. Not to be re-implemented.

**Objective:** deliver `ai-run-phase` and `ai-run`, the scenario-driven stub runner,
the runner-override fixture, and user documentation.

**Scope:** `run-phase` and `run` subcommands, `bin/ai-run-phase`, `bin/ai-run`,
`tests/stub/stub-runner.py`, `tests/stub/scenario-implementer-to-git.json`,
`tests/fixtures/runner-override-project/`, `tests/test_phase8.py`, README orchestrator
section, `specification/` cross-reference.

**Acceptance criteria:**

1. A stub scenario driving `Implementer → Tester(FAIL) → Debugger → Tester(PASS) → Reviewer → Git` completes under `ai-run-phase` with exit 0, `total_runs == 6`, and runner sequence `implementer, tester, debugger, tester, reviewer, git`.
2. Running `o-dev`, `c-test`, `c-rev`, `o-git` and the other aliases manually still works unchanged (§30) — verified via `AI_ROLE_DRYRUN=1`.
3. Replacing the `reviewer` command in a project-local `.ai-run.json` changes the runner that `ai-next --dry-run` resolves and prints, with no modification to any Python source file. The global `config/ai-run.json` is unread for that key, and a second fixture project without the override still resolves the global command. Runner reassignment is therefore a tested guarantee, not documentation.
4. `project-state.md` in every fixture contains no orchestrator counters or execution history after the harness runs (§18, acceptance criterion 18).
5. README documents the four commands, the config file, the runtime files, the stop exit codes, and how to reassign a runner globally or per project.

**Deferred:** the scenarios proving loop continuation and the stop conditions — Phases 8b and 8c.

## Phase 8b — Loop Continuation and Circuit Breaker Scenarios

**Objective:** prove the phase-boundary, counter-reset and circuit-breaker paths with
offline stub scenarios.

**Scope:** four new scenario files under `tests/stub/` and their test functions in a
new `tests/test_phase8b.py`, following the structure of `tests/test_phase8.py`
(`setup_test_directory()`, `git init -b main`, `.gitignore` covering
`.ai-run-state.json`, `.ai-run.log` and `.ai-run.json`).

No change to `airun/`, `bin/`, `config/`, `README.md`, `tests/stub/stub-runner.py`
or `tests/test_phase8.py`. The existing scenario schema — `description`, `next_role`,
`active_phase`, `human_intervention`, `reason`, `exit_code` — expresses every scenario
required by this phase and by Phase 8c. If a required scenario cannot be expressed
within it, stop and escalate rather than extending the schema.

**Acceptance criteria:**

1. Under `ai-run-phase`, a scenario whose final step changes `Active Phase` exits 0, launches no runner for the new phase, and records `total_runs` equal to that scenario's step count (§16).
2. Under `ai-run`, a scenario spanning two consecutive phases exits 0; the second phase's first Implementer resolves to `implementer`, not `senior_implementer`; and after the phase boundary `.ai-run-state.json` shows `phase` set to the second phase with per-role counters and `total_runs` reset, so `total_runs` reflects only the second phase's executions (§19).
3. A scenario issuing five Debugger requests in one phase launches `debugger` once and `senior_debugger` three times, then stops on the fifth request with exit 2 and rule `§8` (`senior_debugger_max == 3`).
4. A scenario producing 15 executions in one phase stops before the sixteenth with exit 2 and rule `§20` (`phase_max_executions == 15`).

**Scenario design constraints:**

* The stub runner commits and pushes after every step, so the git handoff guard is satisfied at Tester transitions; scenarios must not otherwise dirty the working tree.
* Criterion 4's scenario must not route through Git Assistant mid-phase — a Git Assistant step that sets `Next Role: Implementer` without advancing `Active Phase` trips the phase-advance guardrail (Phase 7 AC 8) and stops the loop before the execution limit is reached. Alternating `Implementer`/`Tester` reaches 15 executions without tripping any role-specific limit.
* Criterion 3's scenario must keep `total_runs` below 15 so that `§20` cannot pre-empt `§8`; routing evaluates the phase execution limit before role-specific limits (Phase 4 AC 12).

**Deferred:** the three hard-stop scenarios — Phase 8c.

**Amended 2026-09-03.** Criteria 1 and 2 are worded in terms of `Active Phase`
changing. Under the §19 amendment the trigger is successful Git Assistant
execution. Observable outcomes are unchanged: in both
`scenario-phase-boundary.json` and `scenario-cross-phase.json` the phase change is
performed by the Git Assistant step, so termination point, `total_runs` and
counter-reset behaviour are identical under either reading. The scenarios and
tests require no modification.

## Phase 8c — Stop Condition Scenarios

**Objective:** prove that both loop commands halt on Architect handoff, human
intervention and runner failure.

**Scope:** three new scenario files under `tests/stub/` and their test functions in a
new `tests/test_phase8c.py`. Same constraints as Phase 8b: no change to `airun/`,
`bin/`, `config/`, `README.md`, `stub-runner.py` or the earlier test files.

**Acceptance criteria:**

1. A scenario setting `Next Role: Architect` stops both `ai-run-phase` and `ai-run` with exit 2 and rule `§12`, and launches no further runner (§12).
2. A scenario setting `Human Intervention Required: Yes` stops both `ai-run-phase` and `ai-run` with exit 2 and rule `§13`, and launches no further runner (§13).
3. A stub step returning a non-zero exit stops both `ai-run-phase` and `ai-run` with exit 3, reporting phase, logical role, runner and exit status, with no retry and no subsequent launch (§23).
4. In all three scenarios the executed step's counter is still recorded in `.ai-run-state.json`, so a stop does not lose the execution (Phase 7 AC 11).

**Deferred:** everything listed in specification §32.
---

# 5. Specification Acceptance Criteria Coverage

| Spec §33 criterion | Delivered by |
|---|---|
| 1. Dry-run resolves every supported role | Phase 4 AC 1–11, Phase 5 AC 2 |
| 2. First Implementer → ordinary | Phase 4 AC 1 |
| 3. Later Implementer → senior | Phase 4 AC 2 |
| 4. Every Debugger → senior (amended) | Phase 12 AC 1 |
| 5. Ordinary Debugger tier retired (amended) | Phase 12 AC 1, AC 3 |
| 6. Senior Debugger max 3 | Phase 12 AC 2, Phase 8b AC 3 |
| 7. Architect always stops | Phase 4 AC 6, Phase 5 AC 6, Phase 8c AC 1 |
| 8. Human intervention always stops | Phase 4 AC 7, Phase 8c AC 2 |
| 9. Unknown/malformed always stops | Phase 2 AC 3–5, Phase 4 AC 10, Phase 5 AC 7 |
| 10. Non-advancing role stops | Phase 7 AC 5 |
| 11. Uncommitted/unpushed Tester handoff rejected | Phase 6 AC 1–5 |
| 12. `ai-run-phase` completes a phase | Phase 8a AC 1, Phase 8b AC 1 |
| 13. `ai-run` continues into next phase | Phase 8b AC 2, Phase 10 AC 4 |
| 14. Counters reset on Git Assistant phase completion (amended) | Phase 10 AC 4 |
| 15. Phase circuit breaker | Phase 4 AC 12, Phase 8b AC 4 |
| 16. Runtime failures stop, no retry | Phase 7 AC 6, Phase 8c AC 3 |
| 17. Manual invocation unaffected | Phase 1 AC 3–4, Phase 8a AC 2 |
| 18. `project-state.md` free of counters | Phase 3 (counters only in `.ai-run-state.json`), Phase 8a AC 4 |

---

# 6. Technical Risks

| Risk | Impact | Mitigation |
|---|---|---|
| `opencode run` has no system-prompt flag; the composed lifecycle plus role prompt must be sent as the message body. | Full prompt cost on every OpenCode invocation, same as today's TUI path. | Accepted — matches existing behaviour. Prompt composition stays in `ai-role`, so any future flag is a one-line change. |
| `claude -p --permission-mode auto` grants broad autonomy with no human in the loop. | An unattended role can make wide changes. | Guardrails (circuit breaker, progress validation, git handoff guard) bound the blast radius. `ai-next --dry-run` is the documented way to validate routing before enabling loops. |
| No per-role timeout in this version. | A hung runtime blocks the loop indefinitely. | Accepted for v1; the user can interrupt. A `timeout` key in `limits` is a contained future addition. |
| `git fetch` in the handoff guard requires network access. | Guard fails when offline. | Failure stops automation with a clear message rather than proceeding on stale information — consistent with fail-closed. |
| System Python is 3.9. | 3.10+ syntax would break at import. | No `match`, no `X | Y` annotations, no `dict | dict`. Enforced by running the suite on `/usr/bin/python3`. |
| Phase advancement depends on the Git Assistant honouring an instruction in its prompt. | Cross-phase automation silently mis-tiers the next Implementer. | Phase 1 makes the responsibility explicit; Phase 7 AC 8 adds a deterministic guardrail that stops rather than mis-routing. |

---

# 7. Out of Scope

Everything listed in specification §32, plus: per-role timeouts, retry of failed
runtimes, parsing of agent output for intent, and any automatic repair of
`project-state.md`.

---

# 8. Plan Completion Review

Reviewed after Phase 8c integration.

## Status

All eight implementation phases (1, 2, 3, 4, 5, 6, 7, 8a, 8b, 8c) are delivered,
QA-passed and review-approved. Every criterion in specification §33 is mapped to a
delivered phase in section 5 above, and no criterion is unmapped or partially
covered.

Verification: the four root-level acceptance suites (`test_phase2_ac.py` through
`test_phase6_ac.py`) and the six suites under `tests/` all pass on `/usr/bin/python3`.
The three module-level suites (`test_state.py`, `test_routing.py`, `test_phase3.py`)
import `airun` directly and therefore require the repository root on `PYTHONPATH`;
the stub-harness suites do not.

**Superseded — see section 9.** Investigation on 2026-09-03 found two approved
specification requirements that were never implemented. Section 9 defines the
phases that close them.

## Remaining Candidates

The only outstanding work is the deferred set: specification §32, plus the four
additional exclusions recorded in section 7 (per-role timeouts, runtime retry,
agent-output parsing, automatic `project-state.md` repair).

Specification §32 states these "may be considered later only if an observed need
emerges". Whether such a need has emerged is a scope decision reserved to the user.
The Architect cannot select from this list without expanding approved project scope.

Of the deferred items, the three that section 6 already identifies as bounded and
architecturally contained, should the user wish to extend scope, are:

1. **Per-role timeout** — a `timeout` key under `limits` in `.ai-run.json`, enforced
   in `launcher.py`. Closes the hung-runtime risk recorded in section 6.
2. **Notifications** — a terminal/OS notification on stop, isolated to `logbook.py`.
   Relevant only if the user runs loops unattended.
3. **Dynamic model selection** — already partly expressible through the existing
   per-role command configuration (§24); would require no new architecture.

The remaining §32 items (GUI, web dashboard, daemon, cloud orchestration, AI-based
workflow decisions, automatic Architect execution, workflow DSL, parallel execution,
multi-project orchestration, automatic malformed-state recovery) each contradict a
design principle in specification §2 or a stop rule in §12/§13, and would require a
specification change before any plan could be produced.

---

# 9. Phases 9–11 — Invocation Parity and State Integrity

Added 2026-09-03 following investigation of the first live `ai-run-phase`
execution in the `school-events` project.

## Findings

The loop terminated after one Implementer execution. The Implementer had changed
`Active Phase` from `15.1` to `15.2`; `ai-run-phase` treats any change to that
field as phase completion and exited 0.

Evidence gathered from both projects:

1. **`Active Phase` is not a reliable control signal.** Three of eight Implementer
   state updates in this repository changed it (`e765c9f`, `0968bdd`, `d186f56`),
   manually, with no orchestrator involved. In `school-events` the UI Designer
   changed it as well.
2. **The behaviour is not automation-specific.** `0968bdd` — manual — advanced
   `Active Phase` from Phase 7 to Phase 8, set `Next Role: Implementer`, and left
   `QA: NOT_STARTED`. Phase 7 has no QA report and no review report; it was never
   tested or reviewed. The automated case was milder: it advanced one phase and
   handed to Tester.
3. **Manual routing hides the defect.** A human routes on `Next Role`, so a wrong
   `Active Phase` has no observable effect. The orchestrator routes on
   `Active Phase`, so the same edit becomes a control-flow event.
4. **§16 is partially implemented.** The specification lists "the current phase is
   successfully completed" and "the active phase changes" as separate stop
   conditions. `run_phase_command` implements only the second.
5. **§22 is unimplemented.** "Contradictory workflow state" is a required stop
   condition. Nothing in `airun/` performs any such check.
6. **Two invocation divergences are unjustified.** `--auto` was added at
   implementation time, appears nowhere in the specification, and is unnecessary —
   `opencode run` writes files without it. The kickoff message is appended to
   OpenCode roles, which never receive one under manual invocation.

Findings 4 and 5 are defects against the approved specification, not scope
expansion. Section 6's risk table is amended: the entry accepting the OpenCode
message-body behaviour as "matches existing behaviour" was incorrect — manual
invocation adds no `--auto`.

## Phase 9 — Invocation Parity and Log Correctness

**Objective:** make automated invocation match manual invocation as closely as
non-interactive execution permits, and correct the misleading log field.

**Scope:** `bin/ai-role`, `airun/launcher.py`, `airun/__main__.py`,
`config/ai-run.json`, `tests/fixtures/ai-role-baseline/`, `tests/test_phase8.py`,
and a new `tests/test_phase9.py`.

Add an optional per-role `kickoff` boolean to the role configuration, defaulting
to `true`. `launch_runner` appends `kickoff_prompt` only when it is true. OpenCode
roles set it to `false`, so they receive the composed lifecycle and role prompt as
the message and nothing else — identical in content to manual invocation. Claude
roles keep `kickoff: true`, as §25 requires an initial prompt to create an
execution turn.

Remove `--auto` from both OpenCode batch branches in `ai-role` (execution and
dry-run).

**Acceptance criteria:**

1. `AI_ROLE_DRYRUN=1 AI_ROLE_BATCH=1` for every OpenCode role emits `opencode run` with no `--auto`, and a message equal to the composed lifecycle plus role prompt with no kickoff text appended.
2. The message body in criterion 1 is byte-identical to the message in the corresponding manual baseline fixture; only the subcommand and flag positions differ.
3. `AI_ROLE_DRYRUN=1` without `AI_ROLE_BATCH` still reproduces every committed baseline in `tests/fixtures/ai-role-baseline/` byte-for-byte, for all eleven aliases.
4. Claude roles under batch still emit `claude -p --append-system-prompt … "<kickoff>"`, unchanged.
5. The `done` log line reports the `Next Role` read *after* execution. Currently `airun/__main__.py:213` logs the pre-execution value, so every `done` line names the role that just ran.
6. The baseline check in `tests/test_phase8.py` fails on any byte difference. Its present fallback accepts a match on the first two lines plus marker presence, and would not detect prompt drift.

**Deferred:** all loop-termination and validation behaviour — Phases 10 and 11.

## Phase 10 — Phase Completion Signal

**Approved 2026-09-03.** The specification amendment described below has been
accepted by the user and applied to §16, §19 and §33 criterion 14.

**Superseded 2026-09-03 (Phase 12 QA, Defect 4).** Phase 11's R4 invariant
directly contradicts acceptance criteria 1 and 2 below, and is enabled by
default (`limits.check_phase_change` defaults to `true`, unset in
`config/ai-run.json`). Re-tested against the user, the decision is: **a
mid-phase `Active Phase` edit stops the loop.** R4 is authoritative. This
phase's "pin the phase, don't stop" mechanism (`runtime.py`'s `pinned_phase`)
is retained only as the behaviour that applies if `check_phase_change` is
explicitly disabled in `limits` — it does not run by default and criteria 1–2
below do not hold under default configuration. `tests/test_phase10.py` and
`tests/stub/scenario-phase10-midphase-edit.json`, which asserted the
unconditional (criteria 1–2) behaviour and were bundled into the Phase 12
commit by mistake, have been removed. §16/§19 as amended below describe the
disabled-R4 case only; the default behaviour is governed by Phase 11 §22 R4.

**Objective:** terminate `ai-run-phase` on genuine phase completion rather than on
any change to `Active Phase`.

**Scope:** `airun/__main__.py` (`run_phase_command`, `run_command`),
`airun/runtime.py`, new scenarios under `tests/stub/`, new `tests/test_phase10.py`.

The loop pins the phase identity it started with. That pinned value, not the file,
keys the per-phase counters and the circuit breaker. Mid-phase edits to
`Active Phase` no longer terminate the loop or reset counters. The loop ends when
the Git Assistant completes successfully, which is the §16 condition "the current
phase is successfully completed". Under `ai-run`, Git Assistant completion is also
the point at which the pinned phase advances and counters reset.

This rests on the user's confirmation that the Git Assistant closes every phase,
and that a phase ending without it indicates a problem requiring intervention —
which is itself a stop.

**Acceptance criteria:**

1. A scenario in which a non-Git role changes `Active Phase` mid-phase runs to Git Assistant completion under `ai-run-phase`, exits 0, and does not terminate at the edit.
2. Per-role counters and `total_runs` are unaffected by that mid-phase edit; the circuit breaker still counts from the phase start.
3. `ai-run-phase` exits 0 when the Git Assistant completes, and launches no runner for the next phase.
4. Under `ai-run`, the pinned phase advances and counters reset at Git Assistant completion; the next phase's first Implementer resolves to `implementer`, not `senior_implementer`.
5. A phase that reaches the execution limit without Git Assistant completion still stops with exit 2 and rule `§20`.
6. Existing Phase 8b and 8c scenarios continue to pass unchanged.

**Specification amendment (applied).** §16's "the active phase changes" stop
condition is removed. §19 now keys phase detection and counter reset to Git
Assistant completion, and states that mid-phase `Active Phase` edits by other
roles must not reset counters or terminate a loop. §33 criterion 14 is reworded
accordingly. Phases 9 and 11 do not depend on this amendment.

## Phase 11 — Contradictory State Validation (§22)

**Objective:** implement the §22 stop condition for contradictory workflow state.

**Scope:** new `airun/invariants.py`, called from `airun/__main__.py` after each
role execution and before the next resolution; new scenarios under `tests/stub/`;
new `tests/test_phase11.py`. No change to role prompts.

Four conservative rules, chosen to be unambiguous and to avoid false stops. Each
stops with exit 2 and rule `§22`, naming the fields in conflict.

* **R1** — `Implementation: COMPLETED` with `QA: NOT_STARTED` and `Next Role` an Implementer tier. Work handed onward untested. Catches `0968bdd`.
* **R2** — `Next Role: Reviewer` while `QA` is not a pass state.
* **R3** — `Next Role: Git Assistant` while `Review` is not an approval state.
* **R4** — `Active Phase` changed by any role other than the Git Assistant. Reported as a contradiction rather than silently absorbed. Configurable via `limits`, default enabled. This is the authoritative mid-phase-edit behaviour (stop) per the Phase 10/11 conflict resolution recorded in Phase 10 above; Phase 10's continuation mechanism only applies when this is explicitly disabled.

Rules are evaluated only on the post-execution state of a role the orchestrator
itself launched. Manual operation is unaffected (§30).

**Acceptance criteria:**

1. A scenario reproducing `0968bdd` — Implementer sets `Implementation: COMPLETED`, `QA: NOT_STARTED`, `Next Role: Implementer` — stops with exit 2 and rule `§22`, naming R1.
2. A scenario handing to Reviewer with `QA: FAIL` stops with exit 2 and rule `§22` (R2).
3. A scenario handing to Git Assistant without review approval stops with exit 2 and rule `§22` (R3).
4. A scenario in which the Implementer changes `Active Phase` stops with exit 2 and rule `§22` (R4), and does not stop when R4 is disabled in `limits`.
5. The full normal path of `scenario-implementer-to-git.json` triggers no rule and still exits 0 with `total_runs == 6`.
6. Phase 8b and 8c scenarios continue to pass unchanged.

**Deferred:** any automatic repair of contradictory state, which §22 forbids and
§32 excludes. The orchestrator stops and reports; the user decides.

## Not in scope

Role and lifecycle definitions are unchanged by these phases. `role-lifecycle.md`
and six of the seven role prompts are byte-identical to their pre-project state;
`prompts/role-git.md` gained a thirteen-line "Phase Advancement" section in Phase 1.
Assigning explicit field ownership in the role prompts would be a governance
change affecting manual operation, and is a separate user decision.

The rationale sentence in that added section justifies the instruction in
orchestrator terms — counter resets and senior-tier routing. Restating it in
workflow terms is a one-line prompt edit, listed here for visibility only.

## Phase 12 — Debugger Tier Retirement

**Approved 2026-09-03.** Specification §5, §6, §8 and §33 criteria 4–5 amended
accordingly.

**Objective:** resolve every Debugger request to the senior debugger, bounded by a
single limit.

**Scope:** `airun/routing.py` (debugger branch, currently lines 133–163),
`config/ai-run.json`, `test_phase4_ac.py`, `tests/stub/scenario-debugger-limit.json`,
`tests/test_phase8b.py`, `README.md`.

Remove the `debugger` runner from the role configuration. Every `Next Role:
Debugger` resolves to the `senior_debugger` runner and increments the
`senior_debugger` counter, so `senior_debugger_max` bounds all debugging in a
phase. The `debugger` key is retained in the runtime counters dictionary so the
`.ai-run-state.json` schema version is unchanged; it remains zero.

This phase is independent of Phases 9–11 and may be implemented in any order
relative to them.

**Acceptance criteria:**

1. The first `Next Role: Debugger` in a phase resolves to runner `senior_debugger`, not `debugger`.
2. The second and third resolve to `senior_debugger`, and the fourth stops with exit 2 and rule `§8` — three debugger executions per phase in total, not four.
3. `config/ai-run.json` contains no `debugger` role, and a project-local `.ai-run.json` that overrides `senior_debugger` changes the resolved runner.
4. `.ai-run-state.json` retains `schema: 1` and its existing counter keys; `debugger` stays at zero across a phase containing three debugger executions.
5. `scenario-debugger-limit.json` is updated to the three-execution ceiling, and Phase 8b's other three scenarios pass unchanged.
6. README's runner table and the documented debug sequence match the amended §8.

**Risk:** the previous ceiling allowed one ordinary plus three senior executions.
The amended ceiling is three total, so a phase that previously escalated to human
investigation on the fifth Debugger request now does so on the fourth. This is
intentional — the retired tier was the wasted cycle — but it shortens the
automatic debug budget by one round-trip.
