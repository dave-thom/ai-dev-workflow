"""Launcher for runner subprocesses."""

import subprocess
import os
import sys
from typing import List, Dict, Optional, Tuple

from airun.state import ProjectState


def launch_runner(
    command: List[str],
    kickoff_prompt: str,
    workdir: str,
) -> subprocess.CompletedProcess:
    """
    Launch a runner subprocess with batch mode enabled.
    
    Args:
        command: Base command list from configuration
        kickoff_prompt: Kickoff prompt to append
        workdir: Working directory for the subprocess
        
    Returns:
        CompletedProcess with returncode and stdout/stderr
        
    The command is executed with AI_ROLE_BATCH=1 set in the environment
    and the kickoff_prompt appended as the final argument.
    """
    # Build the full command
    full_command = command.copy()
    full_command.append(kickoff_prompt)
    
    # Prepare environment with batch mode
    env = os.environ.copy()
    env["AI_ROLE_BATCH"] = "1"
    
    # Launch subprocess
    process = subprocess.run(
        full_command,
        cwd=workdir,
        env=env,
        capture_output=False,  # Inherit stdout/stderr for visibility
        text=False,
    )
    
    return process


def check_progress(
    original_state: ProjectState,
    new_state: ProjectState,
    logical_role: str,
) -> Tuple[bool, Optional[str]]:
    """
    Check if progress occurred after a role execution.
    
    Progress is defined as:
    - Human Intervention Required changed to Yes
    - Active Phase changed
    - Next Role differs from the logical role just invoked
    
    Args:
        original_state: ProjectState before execution
        new_state: ProjectState after execution
        logical_role: The logical role that was just invoked
        
    Returns:
        Tuple of (progress_made, reason_if_no_progress)
    """
    # Rule 1: Human intervention changed to Yes
    if not original_state.human_intervention and new_state.human_intervention:
        return True, None
    
    # Rule 2: Active Phase changed
    if original_state.active_phase != new_state.active_phase:
        return True, None
    
    # Rule 3: Next Role changed (and is different from invoked role)
    if original_state.next_role != new_state.next_role:
        return True, None
    
    # No progress
    return False, f"{logical_role} returned same Next Role: {new_state.next_role}"


def check_phase_advance_guardrail(
    original_state: ProjectState,
    new_state: ProjectState,
    logical_role: str,
) -> Optional[str]:
    """
    Check phase-advance guardrail for Git Assistant.
    
    When the logical role was Git Assistant and it exited zero:
    - If Next Role is Implementer but Active Phase is unchanged, stop
    
    Args:
        original_state: ProjectState before execution
        new_state: ProjectState after execution
        logical_role: The logical role that was just invoked
        
    Returns:
        Error message if guardrail triggered, None otherwise
    """
    if logical_role.lower() not in ["git assistant", "git"]:
        return None
    
    if original_state.active_phase == new_state.active_phase:
        if new_state.next_role.lower() in ["implementer", "senior implementer"]:
            return "Git Assistant did not advance Active Phase"
    
    return None