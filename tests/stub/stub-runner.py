#!/usr/bin/env python3
"""Stub runner for testing the ai-run orchestrator.

This script simulates role behavior by reading scenario files and
updating project-state.md accordingly.
"""

import json
import os
import sys
import time
from pathlib import Path


def main():
    """Main entry point for stub runner."""
    # Read scenario from environment variable
    scenario_file = os.environ.get("STUB_SCENARIO")
    if not scenario_file:
        print("STUB_SCENARIO environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    # Read step from environment variable
    try:
        step = int(os.environ.get("STUB_STEP", "0"))
    except ValueError:
        step = 0
    
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
    
    # Exit with configured code
    exit_code = current_step.get("exit_code", 0)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()