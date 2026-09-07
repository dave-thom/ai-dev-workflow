"""Guards for git handoff and ignore-file validation."""

import os
import subprocess
import sys
from typing import Optional, Tuple


# Paths a role is required to write but may not be authorised to commit. Changes
# confined to these paths do not affect the code under test, so they must not
# block a Tester handoff (only the Git Assistant may commit them, and it does not
# always run between two Testers).
#
# project-state.md is included because role-lifecycle.md requires every role to
# update it before handing off, while the Tester and Reviewer are forbidden to
# create commits. Without this exemption a Tester -> Tester or Reviewer -> Tester
# handoff deadlocks on a file no role in that loop is authorised to clear.
DELIVERABLE_PREFIXES = (
    "docs/qa/",
    "docs/debug/",
    "docs/reviews/",
    "project-state.md",
)


def check_ignore_guard(workdir: str) -> Optional[str]:
    """
    Check that .ai-run-state.json and .ai-run.log are git-ignored.
    
    Returns None if both paths are ignored, or an error message if not.
    """
    # Paths to check
    runtime_path = os.path.join(workdir, ".ai-run-state.json")
    log_path = os.path.join(workdir, ".ai-run.log")
    
    # Check if working directory is a git repository
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=workdir,
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Not a git repository, skip the check
        return None
    
    # Check each path
    for path in [runtime_path, log_path]:
        try:
            result = subprocess.run(
                ["git", "check-ignore", "-q", path],
                cwd=workdir,
                capture_output=True,
            )
            if result.returncode != 0:
                return f".ai-run-state.json and .ai-run.log must be git-ignored"
        except Exception as e:
            return f"Failed to check git ignore status: {e}"
    
    return None


def check_git_handoff_guard(
    workdir: str,
    expected_branch: str,
    allow_recovery: bool = True,
) -> Optional[str]:
    """
    Check git handoff guard conditions for Tester role.

    Returns None if all conditions pass, or an error message if any fail.

    With allow_recovery, a branch mismatch that can be resolved safely is
    resolved by checking the expected branch out rather than stopping the run.
    Callers must pass allow_recovery=False for a dry run, which reports what a
    real run would do without touching the repository.
    """
    # Check if working directory is a git repository
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=workdir,
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "Working directory is not a git repository"
    
    # 1. Check for uncommitted changes, ignoring role deliverables.
    #    This runs before the branch check so that the recovery below can only
    #    switch branches when there is no unsaved work to carry across.
    uncommitted = _check_uncommitted(workdir)
    if uncommitted:
        return uncommitted

    # 2. Check current branch, recovering automatically where that is safe
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            cwd=workdir,
            capture_output=True,
            text=True,
            check=True,
        )
        current_branch = result.stdout.strip()
    except subprocess.CalledProcessError:
        return "Cannot determine current branch"

    if current_branch != expected_branch:
        mismatch = (
            f"Current branch '{current_branch}' does not match expected "
            f"'{expected_branch}'"
        )
        if not _branch_exists(workdir, expected_branch):
            return f"{mismatch} ('{expected_branch}' does not exist locally)"
        if not allow_recovery:
            # A dry run must not touch the repository. Report the switch a real
            # run would make; the upstream checks below would be evaluated
            # against the expected branch, so they are left to that real run.
            print(
                f"Git handoff guard: would switch from '{current_branch}' to "
                f"'{expected_branch}'; upstream checks deferred to the real run",
                file=sys.stderr,
            )
            return None
        # The tree holds no work outside the exempt paths, so switching is safe
        # and is what the operator would have to do by hand anyway.
        checkout = subprocess.run(
            ["git", "checkout", expected_branch],
            cwd=workdir,
            capture_output=True,
            text=True,
        )
        if checkout.returncode != 0:
            return f"{mismatch} (git checkout {expected_branch} failed)"
        print(
            f"Git handoff guard: switched from '{current_branch}' to "
            f"'{expected_branch}'",
            file=sys.stderr,
        )

    # 3. Check for upstream
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            cwd=workdir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return "No upstream branch configured"
        
        upstream_ref = result.stdout.strip()
        if not upstream_ref:
            return "No upstream branch configured"
        
        # Parse remote and branch from upstream ref
        if "/" not in upstream_ref:
            return f"Invalid upstream reference: {upstream_ref}"
        
        remote, branch = upstream_ref.split("/", 1)
        
        # 4. Fetch and check if local HEAD matches upstream
        try:
            subprocess.run(
                ["git", "fetch", remote, branch],
                cwd=workdir,
                capture_output=True,
                check=True,
            )
            
            # Get local HEAD
            local_head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=workdir,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            
            # Get upstream HEAD
            upstream_head = subprocess.run(
                ["git", "rev-parse", f"{remote}/{branch}"],
                cwd=workdir,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            
            if local_head != upstream_head:
                return f"Local HEAD differs from upstream"
                
        except subprocess.CalledProcessError as e:
            return f"Failed to fetch or compare with upstream: {e}"
            
    except subprocess.CalledProcessError as e:
        return f"Cannot check upstream: {e}"
    
    return None

def _check_uncommitted(workdir: str) -> Optional[str]:
    """Return an error if the tree holds changes outside the exempt paths."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "-z"],
            cwd=workdir,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return "Cannot check git status"

    # -z gives NUL-terminated, never-quoted records of the form "XY path".
    # A rename also emits its original path as a bare trailing record.
    for record in result.stdout.split("\0"):
        if not record:
            continue
        path = record[3:] if record[2:3] == " " else record
        if not path.startswith(DELIVERABLE_PREFIXES):
            return "Uncommitted changes present"

    return None


def _branch_exists(workdir: str, branch: str) -> bool:
    """Return True if the named local branch exists."""
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=workdir,
        capture_output=True,
    )
    return result.returncode == 0
