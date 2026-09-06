# AI Platform — User Guide

Version: 1.0

How to configure the `ai-run` orchestrator and drive a project through the role
workflow.

---

## 1. What It Does

`ai-run` reads `project-state.md` in your **current working directory**, decides which
role should run next, launches that role as a Claude Code or OpenCode subprocess, then
re-reads the state to confirm progress was made.

The role updates `project-state.md` before it exits. That update is what moves the
workflow forward.

```text
Architect → Implementer → Tester → Reviewer → Git Assistant → (next phase)
                             ↓ FAIL
                          Debugger → Tester
```

---

## 2. One-Time Setup

Add to `~/.zshrc`:

```bash
export AI_PLATFORM="/path/to/ai-dev-workflow"
export PATH="$AI_PLATFORM/bin:$PATH"
```

`AI_PLATFORM` is required — `ai-role` exits immediately without it.

Install at least one runtime: `claude`, `opencode`, or both.

Verify:

```bash
echo "$AI_PLATFORM"
command -v ai-next ai-role claude
```

---

## 3. Initialise A New Project

From inside your project directory:

```bash
cp "$AI_PLATFORM/templates/CLAUDE.md"        ./CLAUDE.md
cp "$AI_PLATFORM/templates/project-state.md" ./project-state.md
cat "$AI_PLATFORM/templates/.gitignore"     >> ./.gitignore
mkdir -p docs/qa docs/debug docs/reviews
```

Then edit `project-state.md`: set `Name`, and set `Branch` to the branch the workflow
will run on.

### Git requirements

Two guards will stop the run if these are not satisfied:

1. **Ignore guard** (every run) — `.ai-run-state.json` and `.ai-run.log` must be
   git-ignored. Copying the template `.gitignore` handles this.
2. **Tester handoff guard** (before each Tester launch) — the working tree must be
   clean, the current branch must equal `Branch` in `project-state.md`, an upstream
   must be configured, and local `HEAD` must equal the upstream after a fetch.

A remote is therefore mandatory. If you have no hosted remote, a local bare repository
works offline and needs no credentials:

```bash
git init -b main
git init --bare ../myproject-remote.git
git remote add origin ../myproject-remote.git
git add -A && git commit -m "Initial commit"
git push -u origin main
```

### Write the plan

The Architect is **never launched automatically**. Run it yourself:

```bash
ai-role claude architect
```

It produces `myplan.md`. Then set `Active Phase`, `Next Role: Implementer` and
`Next Action` in `project-state.md`, and you are ready to run.

---

## 4. Commands

| Command                | Behaviour                                                |
| ---------------------- | -------------------------------------------------------- |
| `ai-next --dry-run`    | Print the routing decision. Launches nothing.             |
| `ai-next`              | Execute exactly one role transition.                      |
| `ai-run-phase`         | Repeat until the Git Assistant completes the active phase. |
| `ai-run`               | Repeat across phases until the workflow stops.            |

`--dry-run` exists on `ai-next` only. All commands must be run from the project root —
they resolve `project-state.md` from the current directory.

Start with `ai-next --dry-run` whenever you are unsure what the state will do. It
validates the state file, config and routing without spending tokens.

---

## 5. Configuration

Two files, merged at run time.

**Global:** `$AI_PLATFORM/config/ai-run.json` — the defaults for every project.

**Project-local:** `.ai-run.json` in the project root — optional overrides.

Merge rules:

* `kickoff_prompt` — replaced if present
* `roles` — merged per role key; a local role entry replaces the global one entirely
* `limits` — merged per limit key

### Changing which runner a role uses

Create `.ai-run.json` in the project and override only what you need:

```json
{
  "roles": {
    "implementer": {
      "command": ["ai-role", "claude", "implementer", "--model", "sonnet", "--permission-mode", "auto"],
      "kickoff": true
    },
    "senior_debugger": {
      "command": ["ai-role", "opencode", "debugger", "-m", "openrouter/deepseek/deepseek-v4-pro"],
      "kickoff": false
    }
  },
  "limits": {
    "phase_max_executions": 10
  }
}
```

`command` is an argv list, not a shell string — every element must be a separate
string. `kickoff` controls whether `kickoff_prompt` is appended as the final argument;
it defaults to `true`. Claude runners generally want `true`; OpenCode runners in the
shipped config use `false` because the composed role prompt is already the message.

To change only the model, edit the model argument in the `command` list.

### Runner keys

Routing resolves a logical role to one of these keys. The key names are fixed — the
commands behind them are yours to change.

| Key                  | Used when                                                   |
| -------------------- | ----------------------------------------------------------- |
| `implementer`        | First Implementer run of a phase                             |
| `senior_implementer` | Second and later Implementer runs in the same phase          |
| `tester`             | Tester                                                       |
| `senior_debugger`    | Every Debugger request — the ordinary tier is retired        |
| `reviewer`           | Reviewer                                                     |
| `git`                | Git Assistant                                                |
| `designer`           | UI Designer                                                  |

There is no `architect` key. The Architect is never launched by the orchestrator.

### Limits

All three are required in the merged config.

| Limit                   | Default | Effect                                          |
| ----------------------- | ------- | ----------------------------------------------- |
| `senior_debugger_max`   | 3       | Debugger runs allowed per phase                  |
| `designer_max`          | 2       | Designer runs allowed per phase                  |
| `phase_max_executions`  | 15      | Total role runs allowed per phase                |

Counters are per phase and reset when the Git Assistant changes `Active Phase`.

---

## 6. Running A Role Directly

`ai-role` composes `role-lifecycle.md` + `prompts/role-<role>.md` and launches the
runtime. Use it for the Architect, or to drive a single role by hand.

```bash
ai-role <claude|opencode> <role> [runtime arguments...]

ai-role claude architect
ai-role claude reviewer --model sonnet
ai-role opencode implementer -m openrouter/deepseek/deepseek-v3.2
```

Roles: `architect`, `designer`, `implementer`, `tester`, `debugger`, `reviewer`, `git`.

Add a role by dropping `prompts/role-<name>.md` into the platform.

Environment flags:

| Variable            | Effect                                                    |
| ------------------- | --------------------------------------------------------- |
| `AI_ROLE_DEBUG=1`   | Print the resolved paths and prompt sizes before launching |
| `AI_ROLE_DRYRUN=1`  | Print the command that would run, then exit                |
| `AI_ROLE_BATCH=1`   | Non-interactive mode. `ai-run` sets this automatically     |

---

## 7. Exit Codes

| Code | Meaning                                                                     |
| ---- | --------------------------------------------------------------------------- |
| `0`  | Transition completed, or the loop finished normally                          |
| `2`  | Stopped — human action required (Architect, escalation, limit, no progress)  |
| `3`  | Runtime failure — a runner exited non-zero                                   |
| `4`  | Invalid state or configuration, or an ignore-guard violation                 |
| `1`  | Unexpected internal error                                                    |

Exit `2` is normally a *correct* stop, not a crash. Read the message.

---

## 8. Runtime Files

Both are written to the project root and must stay git-ignored.

* `.ai-run-state.json` — per-phase run counters. Delete it to reset counters.
* `.ai-run.log` — one line per orchestration event:

```text
13:04:11 Phase 3 | launch   | implementer -> implementer
13:18:42 Phase 3 | done     | implementer -> implementer (exit=0 next=Tester)
13:18:42 Phase 3 | stop     | debugger (Senior debugger limit reached (3/3) (§8))
```

---

## 9. Is It Running, Or Is It Stuck?

Claude-backed roles run under `claude -p`, which prints **nothing** until the whole run
finishes. `ai-run` inherits that output, so after `Launching tester -> tester...` the
terminal stays silent for the entire run. A role that runs a real test suite can be quiet
for several minutes — a 22-fixture eval suite against a live API took 6m15s. Silence is
not a hang.

To confirm from another terminal:

```bash
ps -eo pid,etime,command | grep -E "tsx|npm|claude" | grep -v grep
```

`etime` is how long each process has been alive (`MM:SS`, or `HH:MM:SS` past an hour), and
the command column shows what the role is executing *right now* — a test run, a build, a
git command. If the runner is listed and the command it is running keeps changing between
checks, it is working. Adjust the pattern to your project's toolchain (`pytest`, `go test`,
`cargo`, ...).

If nothing matches, the run has actually ended — read the last line of `.ai-run.log`.

---

## 10. Common Stops

| Message                                        | Cause and fix                                                              |
| ---------------------------------------------- | -------------------------------------------------------------------------- |
| `Architect must never be launched (§12)`       | Normal terminal state. Run `ai-role claude architect`, then set the next phase manually. |
| `Human intervention required (§13)`            | A role escalated. Read `Reason` in `project-state.md`, resolve it, set the field back to `No`. |
| `Cannot read .../project-state.md`             | Wrong working directory. `cd` to the project root.                          |
| `Missing required fields`                      | A field was deleted from `project-state.md`. Restore the template schema.   |
| `Ignore guard violation`                       | Add `.ai-run-state.json` and `.ai-run.log` to `.gitignore`.                 |
| `Git handoff guard violation`                  | Commit and push before the Tester runs; check the branch matches `Branch`.  |
| `No progress: <role> returned same Next Role`  | The role exited without updating `project-state.md`. Inspect its output.    |
| `Senior debugger limit reached (§8)`           | The phase is fighting back. Fix it by hand or split the phase.              |
| `Phase execution limit reached (§20)`          | The phase is looping. Raise `phase_max_executions` or split the phase.      |
| `Contradictory workflow state detected (§22)`  | A role wrote an impossible state, e.g. `Next Role: Reviewer` while QA is not PASS. Correct the state file. |

---

## 11. Typical Session

```bash
cd ~/projects/myproject

ai-next --dry-run     # confirm what will happen
ai-run-phase          # run one complete phase
tail -f .ai-run.log   # watch it, in another terminal

# still going, or stuck? (another terminal — see section 9)
ps -eo pid,etime,command | grep -E "tsx|npm|claude" | grep -v grep

ai-run                # run to the end of the plan
```

When the plan is exhausted, the Git Assistant sets `Next Role: Architect` and the next
routing decision stops with `§12`. That is the successful end of a project.
