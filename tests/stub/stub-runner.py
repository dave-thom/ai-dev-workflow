#!/usr/bin/env python3
"""Stub runner for testing the ai-run orchestrator.

This script simulates role behavior by reading scenario files and
updating project-state.md accordingly.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

STEP_FILE = ".stub-step"


def _read_step():
    if os.path.exists(STEP_FILE):
        try:
            with open(STEP_FILE, "r") as f:
                return int(f.read().strip())
        except (ValueError, IOError):
            pass
    try:
        return int(os.environ.get("STUB_STEP", "0"))
    except ValueError:
        return 0


def _write_next_step(step):
    try:
        with open(STEP_FILE, "w") as f:
            f.write(str(step + 1))
    except IOError:
        pass


def main():
    """Main entry point for stub runner."""
    scenario_file = os.environ.get("STUB_SCENARIO")
    if not scenario_file:
        print("STUB_SCENARIO environment variable not set", file=sys.stderr)
        sys.exit(1)

    step = _read_step()
    
    # Load scenario
    try:
        with open(scenario_file, "r") as f:
            scenario = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"Failed to load scenario: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Check if we have steps left
    if step >= len(scenario):
        print(f"No more steps in scenario (step={step}, total={len(scenario)})", file=sys.stderr)
        sys.exit(0)
    
    # Get current step
    current_step = scenario[step]
    
    # Update project-state.md
    state_file = Path("project-state.md")
    if not state_file.exists():
        print(f"project-state.md not found", file=sys.stderr)
        sys.exit(1)
    
    # Read current state
    try:
        content = state_file.read_text()
    except IOError as e:
        print(f"Failed to read project-state.md: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Parse and update state
    lines = content.splitlines()
    updated = False
    
    for i, line in enumerate(lines):
        if line.startswith("Next Role:"):
            new_role = current_step.get("next_role")
            if new_role:
                lines[i] = f"Next Role: {new_role}"
                updated = True
        elif line.startswith("Active Phase:"):
            new_phase = current_step.get("active_phase")
            if new_phase:
                lines[i] = f"Active Phase: {new_phase}"
                updated = True
        elif line.startswith("Human Intervention Required:"):
            new_intervention = current_step.get("human_intervention")
            if new_intervention is not None:
                lines[i] = f"Human Intervention Required: {new_intervention}"
                updated = True
        elif line.startswith("Reason:"):
            new_reason = current_step.get("reason")
            if new_reason:
                lines[i] = f"Reason: {new_reason}"
                updated = True
        elif line.startswith("Implementation:"):
            new_val = current_step.get("implementation")
            if new_val:
                lines[i] = f"Implementation: {new_val}"
                updated = True
        elif line.startswith("QA:"):
            new_val = current_step.get("qa")
            if new_val:
                lines[i] = f"QA: {new_val}"
                updated = True
        elif line.startswith("Review:"):
            new_val = current_step.get("review")
            if new_val:
                lines[i] = f"Review: {new_val}"
                updated = True
    
    # Write updated state
    try:
        state_file.write_text("\n".join(lines))
    except IOError as e:
        print(f"Failed to write project-state.md: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Print what we did
    print(f"Stub: Updated project-state.md (step={step})", file=sys.stderr)
    for key, value in current_step.items():
        if value:
            print(f"  {key}: {value}", file=sys.stderr)

    _write_next_step(step)

    _git_commit_and_push(step)

    # Exit with configured code
    exit_code = current_step.get("exit_code", 0)
    sys.exit(exit_code)


def _git_commit_and_push(step):
    try:
        subprocess.run(
            ["git", "add", "project-state.md", STEP_FILE],
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"stub: step {step}"],
            capture_output=True,
        )
        subprocess.run(
            ["git", "push"],
            capture_output=True,
        )
    except Exception:
        pass


if __name__ == "__main__":
    main()