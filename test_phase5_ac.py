#!/usr/bin/env python3
"""Test Phase 5 acceptance criteria explicitly (ai-next --dry-run).

These are end-to-end tests: they invoke the real bin/ai-next executable as a
subprocess against temporary working directories, exactly as a human/operator
would, rather than calling airun internals directly. Phase 5 is specifically
about the CLI wiring (bin/ai-next -> airun.__main__ -> dry-run output), so the
tests exercise that path.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.resolve()
AI_NEXT = REPO_ROOT / "bin" / "ai-next"
GLOBAL_CONFIG = REPO_ROOT / "config" / "ai-run.json"

SCRATCH_BASE = Path(
    "/private/tmp/claude-501/-Users-dave-dev-projects-ai-dev-workflow/"
    "343d053d-b2d8-4808-8cbf-5241e3d4046d/scratchpad/phase5tests"
)
SCRATCH_BASE.mkdir(parents=True, exist_ok=True)

FAILURES = []


def check(condition, message):
    if not condition:
        FAILURES.append(message)
        print(f"  FAIL: {message}")
    return condition


DEFAULT_STATE_FIELDS = {
    "Name": "Test Project",
    "Status": "In Progress",
    "Active Phase": "Phase 1",
    "Current Role": "PreviousRole",
    "Next Role": "Tester",
    "Next Action": "Do something",
    "Branch": "main",
    "Implementation": "COMPLETED",
    "QA": "NOT_STARTED",
    "Review": "NOT_STARTED",
    "Human Intervention Required": "No",
    "Reason": "None",
}


def write_project_state(workdir: Path, **overrides):
    fields = DEFAULT_STATE_FIELDS.copy()
    fields.update(overrides)
    content = f"""# PROJECT STATE

---

## Project

Name: {fields['Name']}

---

## Workflow

Status: {fields['Status']}

Active Phase: {fields['Active Phase']}

Current Role: {fields['Current Role']}

Next Role: {fields['Next Role']}

Next Action: {fields['Next Action']}

---

## Git

Branch: {fields['Branch']}

---

## Execution

Implementation: {fields['Implementation']}

QA: {fields['QA']}

Review: {fields['Review']}

---

## Current Deliverables

Plan: myplan.md

UI Specification: None

QA Report: None

Debug Report: None

Review Report: None

---

## Escalation

Human Intervention Required: {fields['Human Intervention Required']}

Reason: {fields['Reason']}
"""
    (workdir / "project-state.md").write_text(content)


def make_workdir(name: str) -> Path:
    d = Path(tempfile.mkdtemp(prefix=f"{name}-", dir=str(SCRATCH_BASE)))
    return d


def run_ai_next(workdir: Path, extra_args=None):
    args = [str(AI_NEXT), "--dry-run"] + (extra_args or [])
    result = subprocess.run(
        args,
        cwd=str(workdir),
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


def load_global_config():
    with open(GLOBAL_CONFIG) as f:
        return json.load(f)


# ---------------------------------------------------------------------------

def test_ac1_bin_ai_next_wiring():
    """AC1: bin/ai-next is executable, sets PYTHONPATH, execs python3 -m airun next "$@"."""
    print("Testing AC1: bin/ai-next wiring...")

    st = os.stat(AI_NEXT)
    check(bool(st.st_mode & stat.S_IXUSR), "bin/ai-next is not executable (owner +x bit unset)")

    content = AI_NEXT.read_text()
    check("PYTHONPATH" in content, "bin/ai-next does not reference PYTHONPATH")
    check(
        'python3 -m airun next "$@"' in content,
        "bin/ai-next does not exec 'python3 -m airun next \"$@\"'",
    )
    check("exec " in content, "bin/ai-next does not use exec to invoke python3")

    print("  done" if not FAILURES else "  see failures above")


def test_ac2_and_ac9_dry_run_launch_output():
    """AC2 + AC9: dry-run prints required fields and exits 0 on launch."""
    print("Testing AC2/AC9: dry-run launch output and exit code...")
    
    workdir = make_workdir("ac2")
    # Use Implementer instead of Tester to avoid git handoff guard (Phase 6)
    write_project_state(workdir, **{"Next Role": "Implementer", "Active Phase": "Phase 5"})
    
    rc, out, err = run_ai_next(workdir)
    
    check(rc == 0, f"AC9: expected exit 0 for launch decision, got {rc} (stderr={err!r})")
    for field in [
        "Project:",
        "Active Phase:",
        "Status:",
        "Logical Next Role:",
        "Resolved Runner:",
        "Counters",
        "Command:",
    ]:
        check(field in out, f"AC2: dry-run output missing expected field '{field}'\n---stdout---\n{out}")
    
    check("implementer" in out.lower(), "AC2: expected resolved runner 'implementer' to appear in output")
    
    shutil.rmtree(workdir, ignore_errors=True)


def test_ac3_printed_command_matches_config():
    """AC3: printed command is configured runner command + kickoff prompt as final arg."""
    print("Testing AC3: printed command matches config + kickoff prompt...")
    
    workdir = make_workdir("ac3")
    # Use Implementer instead of Tester to avoid git handoff guard (Phase 6)
    write_project_state(workdir, **{"Next Role": "Implementer", "Active Phase": "Phase 5"})
    
    rc, out, err = run_ai_next(workdir)
    check(rc == 0, f"expected exit 0, got {rc} (stderr={err!r})")
    
    config = load_global_config()
    expected_command = config["roles"]["implementer"]["command"] + [config["kickoff_prompt"]]
    expected_line = f"Command: {' '.join(expected_command)}"
    
    check(
        expected_line in out,
        f"AC3: expected command line not found.\nExpected: {expected_line}\n---stdout---\n{out}",
    )
    check(
        out.split("Command: ", 1)[-1].splitlines()[0].strip().endswith(config["kickoff_prompt"])
        if "Command: " in out else False,
        "AC3: printed command does not end with the kickoff prompt",
    )
    
    shutil.rmtree(workdir, ignore_errors=True)


def test_ac4_dry_run_launches_no_runtime():
    """AC4: dry-run must not actually execute the resolved runner."""
    print("Testing AC4: dry-run launches no runtime (sentinel file check)...")
    
    workdir = make_workdir("ac4")
    sentinel = workdir / "sentinel.txt"
    sentinel_script = workdir / "write_sentinel.py"
    sentinel_script.write_text(
        "import sys\nopen(sys.argv[1], 'w').write('executed')\n"
    )
    
    local_config = {
        "roles": {
            "implementer": {
                "command": ["python3", str(sentinel_script), str(sentinel)]
            }
        }
    }
    (workdir / ".ai-run.json").write_text(json.dumps(local_config))
    
    write_project_state(workdir, **{"Next Role": "Implementer", "Active Phase": "Phase 5"})
    
    rc, out, err = run_ai_next(workdir)
    
    check(rc == 0, f"expected exit 0 for launch decision, got {rc} (stderr={err!r})")
    check(
        not sentinel.exists(),
        "AC4: sentinel file was created — dry-run actually executed the runner!",
    )
    check(
        str(sentinel_script) in out,
        "AC4: expected printed Command to reference the overridden (sentinel) runner script",
    )
    
    shutil.rmtree(workdir, ignore_errors=True)


def test_ac5_no_runtime_files_written():
    """AC5: dry-run writes no .ai-run-state.json and appends no .ai-run.log entry."""
    print("Testing AC5: no runtime state / log files written...")
    
    workdir = make_workdir("ac5")
    # Use Implementer instead of Tester to avoid git handoff guard (Phase 6)
    write_project_state(workdir, **{"Next Role": "Implementer", "Active Phase": "Phase 5"})
    
    rc, out, err = run_ai_next(workdir)
    check(rc == 0, f"expected exit 0, got {rc} (stderr={err!r})")
    
    check(
        not (workdir / ".ai-run-state.json").exists(),
        "AC5: .ai-run-state.json was created by a dry-run",
    )
    check(
        not (workdir / ".ai-run.log").exists(),
        "AC5: .ai-run.log was created by a dry-run",
    )
    
    shutil.rmtree(workdir, ignore_errors=True)


def test_ac6_architect_stop():
    """AC6: dry-run against Architect state prints stop reason, phase, status,
    deliverable pointers, and exits 2."""
    print("Testing AC6: Architect state stops with exit 2...")

    workdir = make_workdir("ac6")
    write_project_state(
        workdir,
        **{"Next Role": "Architect", "Active Phase": "Phase 9", "Status": "Blocked"},
    )

    rc, out, err = run_ai_next(workdir)

    check(rc == 2, f"AC6: expected exit 2, got {rc} (stderr={err!r})\n---stdout---\n{out}")
    check("Phase 9" in out, "AC6: expected active phase 'Phase 9' in output")
    check("Blocked" in out, "AC6: expected status 'Blocked' in output")
    check(
        "must never be launched" in out or "§12" in out,
        "AC6: expected an Architect-specific stop reason (§12) in output",
    )
    check("Plan: myplan.md" in out, "AC6: expected deliverable pointer 'Plan: myplan.md' in output")

    shutil.rmtree(workdir, ignore_errors=True)


def test_ac7_malformed_state_exits_4():
    """AC7: dry-run against malformed project-state.md exits 4."""
    print("Testing AC7: malformed project-state.md exits 4...")

    workdir = make_workdir("ac7")
    (workdir / "project-state.md").write_text("# TEST\n")

    rc, out, err = run_ai_next(workdir)
    check(rc == 4, f"AC7: expected exit 4 for malformed state, got {rc}\n---stdout---\n{out}\n---stderr---\n{err}")

    shutil.rmtree(workdir, ignore_errors=True)


def test_ac8_ignore_guard_exits_4():
    """AC8: dry-run in a git repo where the runtime paths are not git-ignored
    exits 4, naming both runtime paths."""
    print("Testing AC8: un-ignored runtime paths exit 4...")
    
    workdir = make_workdir("ac8")
    subprocess.run(["git", "init", "-q"], cwd=str(workdir), check=True)
    # Rename master to main to match project-state.md
    subprocess.run(["git", "checkout", "-b", "main"], cwd=str(workdir), check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(workdir), check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(workdir), check=True)
    # Create and commit .gitignore (doesn't contain the runtime paths)
    (workdir / ".gitignore").write_text("# empty\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=str(workdir), check=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=str(workdir), check=True)
    
    write_project_state(workdir, **{"Next Role": "Tester", "Active Phase": "Phase 5"})
    # Commit project-state.md to avoid uncommitted changes
    subprocess.run(["git", "add", "project-state.md"], cwd=str(workdir), check=True)
    subprocess.run(["git", "commit", "-m", "Add project state"], cwd=str(workdir), check=True)
    
    rc, out, err = run_ai_next(workdir)
    
    # Should exit 4 because runtime paths are not git-ignored
    check(rc == 4, f"AC8: expected exit 4, got {rc}\n---stdout---\n{out}\n---stderr---\n{err}")
    combined = out + err
    check(".ai-run-state.json" in combined, "AC8: expected '.ai-run-state.json' named in output")
    check(".ai-run.log" in combined, "AC8: expected '.ai-run.log' named in output")
    
    shutil.rmtree(workdir, ignore_errors=True)


def test_ac8_control_ignored_paths_proceed():
    """Control for AC8: same setup, but with a .gitignore covering both paths,
    dry-run should proceed normally (not blocked by the ignore guard)."""
    print("Testing AC8 control: ignored runtime paths proceed normally...")
    
    workdir = make_workdir("ac8-control")
    subprocess.run(["git", "init", "-q"], cwd=str(workdir), check=True)
    # Rename master to main to match project-state.md
    subprocess.run(["git", "checkout", "-b", "main"], cwd=str(workdir), check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(workdir), check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(workdir), check=True)
    (workdir / ".gitignore").write_text(".ai-run-state.json\n.ai-run.log\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=str(workdir), check=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=str(workdir), check=True)
    
    # Set up upstream (bare repo) for git handoff guard
    parent_dir = workdir.parent
    remote_name = f"remote-{workdir.name}.git"
    bare_dir = parent_dir / remote_name
    subprocess.run(["git", "init", "--bare", "-q", str(bare_dir)], cwd=str(workdir), check=True)
    subprocess.run(["git", "remote", "add", "origin", str(bare_dir)], cwd=str(workdir), check=True)
    subprocess.run(["git", "push", "--force", "-u", "origin", "main"], cwd=str(workdir), check=True)
    
    write_project_state(workdir, **{"Next Role": "Tester", "Active Phase": "Phase 5"})
    # Commit project-state.md to avoid uncommitted changes
    subprocess.run(["git", "add", "project-state.md"], cwd=str(workdir), check=True)
    subprocess.run(["git", "commit", "-m", "Add project state"], cwd=str(workdir), check=True)
    # Push the commit
    subprocess.run(["git", "push"], cwd=str(workdir), check=True)
    
    rc, out, err = run_ai_next(workdir)
    check(rc == 0, f"expected exit 0 once paths are ignored, got {rc}\n---stdout---\n{out}\n---stderr---\n{err}")
    
    shutil.rmtree(workdir, ignore_errors=True)


def main():
    tests = [
        test_ac1_bin_ai_next_wiring,
        test_ac2_and_ac9_dry_run_launch_output,
        test_ac3_printed_command_matches_config,
        test_ac4_dry_run_launches_no_runtime,
        test_ac5_no_runtime_files_written,
        test_ac6_architect_stop,
        test_ac7_malformed_state_exits_4,
        test_ac8_ignore_guard_exits_4,
        test_ac8_control_ignored_paths_proceed,
    ]

    for t in tests:
        t()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("All Phase 5 acceptance criteria tests passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
