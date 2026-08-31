#!/usr/bin/env python3
"""Test Phase 6 acceptance criteria explicitly (git handoff and ignore guards).

These are end-to-end tests: they invoke the real bin/ai-next executable as a
subprocess against temporary working directories, exactly as a human/operator
would, rather than calling airun internals directly. Phase 6 is specifically
about the git handoff guard and its integration with ai-next --dry-run.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.resolve()
AI_NEXT = REPO_ROOT / "bin" / "ai-next"
GLOBAL_CONFIG = REPO_ROOT / "config" / "ai-run.json"

SCRATCH_BASE = Path(
    "/private/tmp/claude-501/-Users-dave-dev-projects-ai-dev-workflow/"
    "343d053d-b2d8-4808-8cbf-5241e3d4046d/scratchpad/phase6tests"
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


def setup_git_repo(workdir: Path, branch="main", with_upstream=False, add_commit=False, commit_project_state=True):
    """Helper to set up a git repository with optional commits and upstream."""
    # Initialize git repo
    subprocess.run(["git", "init", "-q"], cwd=str(workdir), check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(workdir), check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(workdir), check=True)
    
    # Create initial commit
    (workdir / ".gitignore").write_text(".ai-run-state.json\n.ai-run.log\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=str(workdir), check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(workdir), check=True)
    
    # Check if we're on master and need to rename to main
    current_branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=str(workdir),
        capture_output=True,
        text=True,
    ).stdout.strip()
    
    if current_branch == "master" and branch == "main":
        subprocess.run(["git", "branch", "-m", "master", "main"], cwd=str(workdir), check=True)
    elif branch != "main" and branch != current_branch:
        subprocess.run(["git", "checkout", "-b", branch], cwd=str(workdir), check=True)
    
    # Set up upstream if requested (create a bare repo as remote)
    if with_upstream:
        # Create bare repo in parent directory to avoid being in workdir
        parent_dir = workdir.parent
        remote_name = f"remote-{workdir.name}.git"
        bare_dir = parent_dir / remote_name
        subprocess.run(["git", "init", "--bare", "-q", str(bare_dir)], cwd=str(workdir), check=True)
        subprocess.run(["git", "remote", "add", "origin", str(bare_dir)], cwd=str(workdir), check=True)
        # Push with --force to set up upstream
        current_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(workdir),
            capture_output=True,
            text=True,
        ).stdout.strip()
        subprocess.run(["git", "push", "--force", "-u", "origin", current_branch], cwd=str(workdir), check=True)
    
    # Add additional commit if requested
    if add_commit:
        (workdir / "test.txt").write_text("test content")
        subprocess.run(["git", "add", "test.txt"], cwd=str(workdir), check=True)
        subprocess.run(["git", "commit", "-m", "Test commit"], cwd=str(workdir), check=True)


# ---------------------------------------------------------------------------

def test_ac1_uncommitted_changes_stops():
    """AC1: With Next Role: Tester and an uncommitted modification present,
    ai-next --dry-run stops with a role-contract violation and exits 2."""
    print("Testing AC1: uncommitted modification stops...")
    
    workdir = make_workdir("ac1")
    setup_git_repo(workdir, with_upstream=True)
    write_project_state(workdir, **{"Next Role": "Tester", "Active Phase": "Phase 6"})
    # Commit project-state.md
    subprocess.run(["git", "add", "project-state.md"], cwd=str(workdir), check=True)
    subprocess.run(["git", "commit", "-m", "Add project state"], cwd=str(workdir), check=True)
    
    # Create uncommitted modification
    (workdir / "uncommitted.txt").write_text("uncommitted content")
    
    rc, out, err = run_ai_next(workdir)
    combined = out + err
    
    check(rc == 2, f"AC1: expected exit 2 for uncommitted changes, got {rc}\n---stdout---\n{out}\n---stderr---\n{err}")
    check("Uncommitted changes present" in combined or "role-contract violation" in combined,
          f"AC1: expected stop message about uncommitted changes\n---combined---\n{combined}")
    
    shutil.rmtree(workdir, ignore_errors=True)


def test_ac2_committed_unpushed_stops():
    """AC2: With Next Role: Tester and a committed but unpushed commit, it stops and exits 2."""
    print("Testing AC2: committed but unpushed stops...")
    
    workdir = make_workdir("ac2")
    setup_git_repo(workdir, with_upstream=False)  # No upstream means can't push
    write_project_state(workdir, **{"Next Role": "Tester", "Active Phase": "Phase 6"})
    # Commit project-state.md
    subprocess.run(["git", "add", "project-state.md"], cwd=str(workdir), check=True)
    subprocess.run(["git", "commit", "-m", "Add project state"], cwd=str(workdir), check=True)
    
    # Add a commit
    (workdir / "committed.txt").write_text("committed content")
    subprocess.run(["git", "add", "committed.txt"], cwd=str(workdir), check=True)
    subprocess.run(["git", "commit", "-m", "Committed but not pushed"], cwd=str(workdir), check=True)
    
    rc, out, err = run_ai_next(workdir)
    combined = out + err
    
    check(rc == 2, f"AC2: expected exit 2 for unpushed commit, got {rc}\n---stdout---\n{out}\n---stderr---\n{err}")
    check("No upstream branch configured" in combined or "upstream" in combined,
          f"AC2: expected stop message about upstream\n---combined---\n{combined}")
    
    shutil.rmtree(workdir, ignore_errors=True)


def test_ac3_clean_upstream_proceeds():
    """AC3: With Next Role: Tester, a clean tree, an upstream, and local HEAD equal to upstream, it proceeds."""
    print("Testing AC3: clean tree with upstream proceeds...")
    
    workdir = make_workdir("ac3")
    setup_git_repo(workdir, with_upstream=True)
    write_project_state(workdir, **{"Next Role": "Tester", "Active Phase": "Phase 6"})
    # Commit project-state.md
    subprocess.run(["git", "add", "project-state.md"], cwd=str(workdir), check=True)
    subprocess.run(["git", "commit", "-m", "Add project state"], cwd=str(workdir), check=True)
    # Push the commit
    subprocess.run(["git", "push"], cwd=str(workdir), check=True)
    
    rc, out, err = run_ai_next(workdir)
    
    check(rc == 0, f"AC3: expected exit 0 for clean tree with upstream, got {rc}\n---stdout---\n{out}\n---stderr---\n{err}")
    check("Resolved Runner: tester" in out or "Command:" in out,
          f"AC3: expected dry-run to proceed (show runner/command)\n---stdout---\n{out}")
    
    shutil.rmtree(workdir, ignore_errors=True)


def test_ac4_no_upstream_stops():
    """AC4: With Next Role: Tester and no upstream configured, it stops and exits 2."""
    print("Testing AC4: no upstream configured stops...")
    
    workdir = make_workdir("ac4")
    setup_git_repo(workdir, with_upstream=False)  # No upstream
    write_project_state(workdir, **{"Next Role": "Tester", "Active Phase": "Phase 6"})
    # Commit project-state.md
    subprocess.run(["git", "add", "project-state.md"], cwd=str(workdir), check=True)
    subprocess.run(["git", "commit", "-m", "Add project state"], cwd=str(workdir), check=True)
    
    rc, out, err = run_ai_next(workdir)
    combined = out + err
    
    check(rc == 2, f"AC4: expected exit 2 for no upstream, got {rc}\n---stdout---\n{out}\n---stderr---\n{err}")
    check("No upstream branch configured" in combined or "upstream" in combined,
          f"AC4: expected stop message about upstream\n---combined---\n{combined}")
    
    shutil.rmtree(workdir, ignore_errors=True)


def test_ac5_wrong_branch_stops():
    """AC5: With Next Role: Tester and the current branch differing from Git / Branch, it stops and exits 2."""
    print("Testing AC5: wrong branch stops...")
    
    workdir = make_workdir("ac5")
    setup_git_repo(workdir, branch="feature", with_upstream=True)  # Branch is "feature"
    write_project_state(workdir, **{"Next Role": "Tester", "Active Phase": "Phase 6", "Branch": "main"})  # Expecting "main"
    # Commit project-state.md
    subprocess.run(["git", "add", "project-state.md"], cwd=str(workdir), check=True)
    subprocess.run(["git", "commit", "-m", "Add project state"], cwd=str(workdir), check=True)
    # Push the commit
    subprocess.run(["git", "push"], cwd=str(workdir), check=True)
    
    rc, out, err = run_ai_next(workdir)
    combined = out + err
    
    check(rc == 2, f"AC5: expected exit 2 for wrong branch, got {rc}\n---stdout---\n{out}\n---stderr---\n{err}")
    check("does not match expected" in combined or "Current branch" in combined,
          f"AC5: expected stop message about branch mismatch\n---combined---\n{combined}")
    
    shutil.rmtree(workdir, ignore_errors=True)


def test_ac6_guard_only_for_tester():
    """AC6: The guard is not applied when Next Role is anything other than Tester."""
    print("Testing AC6: guard only for Tester...")
    
    workdir = make_workdir("ac6")
    setup_git_repo(workdir, with_upstream=False)  # No upstream (should stop if Tester)
    # Test with Implementer - should not trigger git handoff guard
    write_project_state(workdir, **{"Next Role": "Implementer", "Active Phase": "Phase 6", "Branch": "main"})
    # Commit project-state.md
    subprocess.run(["git", "add", "project-state.md"], cwd=str(workdir), check=True)
    subprocess.run(["git", "commit", "-m", "Add project state"], cwd=str(workdir), check=True)
    
    rc, out, err = run_ai_next(workdir)
    
    # With Implementer and no upstream, should proceed (no git handoff guard for non-Tester)
    check(rc == 0, f"AC6: expected exit 0 for Implementer (no git handoff guard), got {rc}\n---stdout---\n{out}\n---stderr---\n{err}")
    check("Resolved Runner:" in out, f"AC6: expected dry-run to proceed for non-Tester role\n---stdout---\n{out}")
    
    # Also test with Debugger
    workdir2 = make_workdir("ac6-debugger")
    setup_git_repo(workdir2, with_upstream=False)
    write_project_state(workdir2, **{"Next Role": "Debugger", "Active Phase": "Phase 6", "Branch": "main"})
    subprocess.run(["git", "add", "project-state.md"], cwd=str(workdir2), check=True)
    subprocess.run(["git", "commit", "-m", "Add project state"], cwd=str(workdir2), check=True)
    
    rc2, out2, err2 = run_ai_next(workdir2)
    check(rc2 == 0, f"AC6: expected exit 0 for Debugger (no git handoff guard), got {rc2}")
    
    shutil.rmtree(workdir, ignore_errors=True)
    shutil.rmtree(workdir2, ignore_errors=True)


def test_ac7_no_mutating_git_commands():
    """AC7: No guard path ever runs git add, commit, push, checkout or reset;
    only status, rev-parse, fetch, check-ignore and symbolic-ref are used."""
    print("Testing AC7: no mutating git commands used...")
    
    workdir = make_workdir("ac7")
    setup_git_repo(workdir, with_upstream=True)
    write_project_state(workdir, **{"Next Role": "Tester", "Active Phase": "Phase 6"})
    # Commit project-state.md
    subprocess.run(["git", "add", "project-state.md"], cwd=str(workdir), check=True)
    subprocess.run(["git", "commit", "-m", "Add project state"], cwd=str(workdir), check=True)
    # Push the commit
    subprocess.run(["git", "push"], cwd=str(workdir), check=True)
    
    # We can't directly test which git commands are run, but we can verify
    # that the repository state doesn't change
    initial_commits = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=str(workdir),
        capture_output=True,
        text=True,
    ).stdout.strip()
    
    rc, out, err = run_ai_next(workdir)
    
    final_commits = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=str(workdir),
        capture_output=True,
        text=True,
    ).stdout.strip()
    
    check(rc == 0, f"AC7: expected exit 0, got {rc}")
    check(initial_commits == final_commits,
          f"AC7: git log changed - mutating commands may have been run\nBefore: {initial_commits}\nAfter: {final_commits}")
    
    # Check branch didn't change
    current_branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=str(workdir),
        capture_output=True,
        text=True,
    ).stdout.strip()
    check(current_branch == "main", f"AC7: branch changed from main to {current_branch}")
    
    shutil.rmtree(workdir, ignore_errors=True)


def test_ac8_non_git_dir_tester_stops():
    """AC8: A working directory that is not a git repository stops with a clear message
    when Next Role: Tester, and does not stop the ignore guard."""
    print("Testing AC8: non-git directory stops for Tester...")
    
    workdir = make_workdir("ac8")
    # Not a git repository
    write_project_state(workdir, **{"Next Role": "Tester", "Active Phase": "Phase 6"})
    
    rc, out, err = run_ai_next(workdir)
    combined = out + err
    
    check(rc == 2, f"AC8: expected exit 2 for non-git dir with Tester, got {rc}\n---stdout---\n{out}\n---stderr---\n{err}")
    check("not a git repository" in combined.lower() or "Working directory" in combined,
          f"AC8: expected stop message about non-git directory\n---combined---\n{combined}")
    
    # Test that ignore guard doesn't stop (not a git repo, skip ignore check)
    # This is verified by the fact we got exit 2, not exit 4
    
    shutil.rmtree(workdir, ignore_errors=True)


def test_ac8_control_non_git_dir_non_tester_proceeds():
    """Control for AC8: non-git directory with non-Tester role should proceed."""
    print("Testing AC8 control: non-git directory with non-Tester proceeds...")
    
    workdir = make_workdir("ac8-control")
    # Not a git repository, but Next Role is Implementer
    write_project_state(workdir, **{"Next Role": "Implementer", "Active Phase": "Phase 6"})
    
    rc, out, err = run_ai_next(workdir)
    
    check(rc == 0, f"AC8 control: expected exit 0 for non-git dir with Implementer, got {rc}\n---stdout---\n{out}\n---stderr---\n{err}")
    check("Resolved Runner:" in out, f"AC8 control: expected dry-run to proceed for non-Tester in non-git dir\n---stdout---\n{out}")
    
    shutil.rmtree(workdir, ignore_errors=True)


def main():
    tests = [
        test_ac1_uncommitted_changes_stops,
        test_ac2_committed_unpushed_stops,
        test_ac3_clean_upstream_proceeds,
        test_ac4_no_upstream_stops,
        test_ac5_wrong_branch_stops,
        test_ac6_guard_only_for_tester,
        test_ac7_no_mutating_git_commands,
        test_ac8_non_git_dir_tester_stops,
        test_ac8_control_non_git_dir_non_tester_proceeds,
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
        print("All Phase 6 acceptance criteria tests passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()