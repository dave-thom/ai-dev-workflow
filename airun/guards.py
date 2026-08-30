"""Guards for git handoff and ignore-file validation."""

import os
import subprocess
from typing import Optional, Tuple


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
) -> Optional[str]:
    """
    Check git handoff guard conditions for Tester role.
    
    Returns None if all conditions pass, or an error message if any fail.
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
    
    # 1. Check current branch
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            cwd=workdir,
            capture_output=True,
            text=True,
            check=True,
        )
        current_branch = result.stdout.strip()
        if current_branch != expected_branch:
            return f"Current branch '{current_branch}' does not match expected '{expected_branch}'"
    except subprocess.CalledProcessError:
        return "Cannot determine current branch"
    
    # 2. Check for uncommitted changes
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=workdir,
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stdout.strip():
            return "Uncommitted changes present"
    except subprocess.CalledProcessError:
        return "Cannot check git status"
    
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