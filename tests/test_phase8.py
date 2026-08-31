#!/usr/bin/env python3
"""Test script for Phase 8 acceptance criteria."""

import os
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path


def setup_test_directory():
    """Create a temporary directory for testing."""
    test_dir = tempfile.mkdtemp(prefix="ai-run-test-")
    print(f"Created test directory: {test_dir}")
    
    # Copy necessary files
    ai_platform = Path(__file__).parent.parent
    
    # Create project-state.md
    state_content = """# PROJECT STATE

This file is the authoritative record of where the project is now.

AI agents read it to determine the active workflow state and next action.

Update existing fields in place. Do not append history, findings, rationale, investigation detail, test evidence, implementation summaries, or completed-task narratives.

Detailed information belongs in the referenced role deliverables.

Do not add new fields or sections unless explicitly instructed to change this schema.

---

## Project

Name: Test Project

---

## Workflow

Status: In Progress

Active Phase: Phase 8

Current Role: Implementer

Next Role: Implementer

Next Action: Test Phase 8 implementation

---

## Git

Branch: main

---

## Execution

Implementation: NOT_STARTED

QA: NOT_STARTED

Review: NOT_STARTED

---

## Current Deliverables

Plan: myplan.md

UI Specification: None

QA Report: None

Debug Report: None

Review Report: None

---

## Escalation

Human Intervention Required: No

Reason: None
"""
    
    state_file = Path(test_dir) / "project-state.md"
    state_file.write_text(state_content)
    
    # Create .ai-run-state.json
    state_json = {
        "schema": 1,
        "phase": "Phase 8",
        "counters": {
            "implementer": 0,
            "senior_implementer": 0,
            "designer": 0,
            "tester": 0,
            "debugger": 0,
            "senior_debugger": 0,
            "reviewer": 0,
            "git": 0
        },
        "total_runs": 0
    }
    
    import json
    state_json_file = Path(test_dir) / ".ai-run-state.json"
    state_json_file.write_text(json.dumps(state_json, indent=2))
    
    # Create .gitignore with required entries
    gitignore_content = """.ai-run-state.json
.ai-run.log
"""
    # Create a git repository
    subprocess.run(["git", "init"], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=test_dir, capture_output=True)
    
    # Create a remote repository
    remote_dir = tempfile.mkdtemp(prefix="ai-run-remote-")
    subprocess.run(["git", "init", "--bare"], cwd=remote_dir, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", remote_dir], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=test_dir, capture_output=True)


def test_ai_run_phase():
    """Test ai-run-phase command with stub runner."""
    print("\n=== Testing ai-run-phase ===")
    
    test_dir, ai_platform = setup_test_directory()
    
    try:
        # Set environment for stub runner
        scenario_file = ai_platform / "tests" / "stub" / "scenario-implementer-to-git.json"
        os.environ["STUB_SCENARIO"] = str(scenario_file)
        os.environ["STUB_STEP"] = "0"
        
        # Create a custom config that uses our stub runner
        config_content = {
            "kickoff_prompt": "Begin test",
            "roles": {
                "implementer": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")]},
                "senior_implementer": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")]},
                "debugger": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")]},
                "senior_debugger": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")]},
                "git": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")]},
                "tester": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")]},
                "reviewer": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")]},
                "designer": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")]}
            },
            "limits": {
                "senior_debugger_max": 3,
                "designer_max": 2,
                "phase_max_executions": 15
            }
        }
        
        config_file = Path(test_dir) / ".ai-run.json"
        import json
        config_file.write_text(json.dumps(config_content, indent=2))
        
        # Change to test directory
        original_cwd = os.getcwd()
        os.chdir(test_dir)
        
        try:
            # Run ai-run-phase
            print("Running ai-run-phase...")
            result = subprocess.run(
                [str(ai_platform / "bin" / "ai-run-phase")],
                capture_output=True,
                text=True
            )
            
            print(f"Exit code: {result.returncode}")
            print(f"Stdout:\n{result.stdout}")
            print(f"Stderr:\n{result.stderr}")
            
            # Check result
            if result.returncode == 0:
                print("✓ ai-run-phase completed successfully")
                
                # Check that phase changed
                state_file = Path("project-state.md")
                state_content = state_file.read_text()
                if "Active Phase: Phase 9" in state_content:
                    print("✓ Phase correctly advanced to Phase 9")
                else:
                    print("✗ Phase did not advance correctly")
                    return False
            else:
                print("✗ ai-run-phase failed")
                return False
                
        finally:
            os.chdir(original_cwd)
            
    finally:
        # Cleanup
        shutil.rmtree(test_dir)
        print(f"Cleaned up test directory")
    
    return True


def main():
    """Run all tests."""
    print("Running Phase 8 acceptance tests...")
    
    tests_passed = True
    
    # Test 1: ai-run-phase
    if not test_ai_run_phase():
        tests_passed = False
    
    if tests_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())