#!/usr/bin/env python3
"""Test script for Phase 10 acceptance criteria."""

import os
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def setup_test_directory(initial_phase="Phase 10"):
    """Create a temporary directory for testing."""
    test_dir = tempfile.mkdtemp(prefix="ai-run-phase10-test-")
    print(f"Created test directory: {test_dir}")
    
    # Copy necessary files
    ai_platform = Path(__file__).parent.parent
    
    # Create project-state.md
    state_content = f"""# PROJECT STATE

This file is the authoritative record of where the project is now.

AI agents read it to determine the active workflow state and next action.

Update existing fields in place. Do not append history, findings, rationale, investigation detail, test evidence, implementation summaries, or completed-task narratives.

Detailed information belongs in the referenced role deliverables.

Do not add new fields or sections unless explicitly instructed to change this schema.

---

## Project

Name: Test Project Phase 10

---

## Workflow

Status: In Progress

Active Phase: {initial_phase}

Current Role: Implementer

Next Role: Implementer

Next Action: Test Phase 10 implementation

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
        "phase": initial_phase,
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
.ai-run.json
"""
    (Path(test_dir) / ".gitignore").write_text(gitignore_content)
    # Create a git repository
    subprocess.run(["git", "init", "-b", "main"], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=test_dir, capture_output=True)
    
    # Create a remote repository
    remote_dir = tempfile.mkdtemp(prefix="ai-run-remote-")
    subprocess.run(["git", "init", "--bare"], cwd=remote_dir, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", remote_dir], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=test_dir, capture_output=True)

    return test_dir, ai_platform


def test_midphase_active_phase_edit():
    """Test AC1: Mid-phase Active Phase edit doesn't terminate loop."""
    print("\n=== Testing AC1: Mid-phase Active Phase edit ===")
    
    test_dir, ai_platform = setup_test_directory("Phase 10")
    
    try:
        # Set environment for stub runner
        scenario_file = ai_platform / "tests" / "stub" / "scenario-phase10-midphase-edit.json"
        os.environ["STUB_SCENARIO"] = str(scenario_file)
        os.environ["STUB_STEP"] = "0"
        
        # Create a custom config that uses our stub runner
        config_content = {
            "kickoff_prompt": "Begin test",
            "roles": {
                "implementer": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True},
                "senior_implementer": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True},
                
                "senior_debugger": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True},
                "git": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True},
                "tester": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True},
                "reviewer": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True},
                "designer": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True}
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
            print("Running ai-run-phase with mid-phase Active Phase edit...")
            result = subprocess.run(
                [str(ai_platform / "bin" / "ai-run-phase")],
                capture_output=True,
                text=True
            )
            
            print(f"Exit code: {result.returncode}")
            print(f"Stderr:\n{result.stderr}")
            
            # Check result - should exit 0 (Git Assistant completed)
            if result.returncode == 0:
                print("✓ ai-run-phase completed successfully")
                
                # Check that phase changed to final phase (Phase 11)
                state_file = Path("project-state.md")
                state_content = state_file.read_text()
                if "Active Phase: Phase 11" in state_content:
                    print("✓ Phase correctly advanced to Phase 11 after Git Assistant")
                else:
                    print("✗ Phase did not advance correctly")
                    print(f"State content:\n{state_content}")
                    return False
                
                # Check counters - should have counts for all executed roles
                state_json_file = Path(".ai-run-state.json")
                if state_json_file.exists():
                    state_json = json.loads(state_json_file.read_text())
                    total_runs = state_json.get("total_runs", 0)
                    # Should be 6 executions in the scenario
                    if total_runs == 6:
                        print(f"✓ Total runs correct: {total_runs}")
                    else:
                        print(f"✗ Total runs incorrect: {total_runs}, expected 6")
                        return False
                else:
                    print("✗ .ai-run-state.json not found")
                    return False
            else:
                print("✗ ai-run-phase failed with exit code", result.returncode)
                print(f"Stdout:\n{result.stdout}")
                return False
                
        finally:
            os.chdir(original_cwd)
            
    finally:
        # Cleanup
        shutil.rmtree(test_dir)
        print(f"Cleaned up test directory")
    
    return True


def test_git_assistant_completion():
    """Test AC3: ai-run-phase exits 0 when Git Assistant completes."""
    print("\n=== Testing AC3: Git Assistant completion ===")
    
    # This is covered by test_midphase_active_phase_edit since it ends with Git Assistant
    # But let's create a simpler test
    test_dir, ai_platform = setup_test_directory("Phase 10")
    
    try:
        # Create a simple scenario that goes straight to Git Assistant
        simple_scenario = [
            {
                "description": "Git Assistant completes phase",
                "next_role": "Implementer",
                "active_phase": "Phase 11",
                "exit_code": 0
            }
        ]
        
        scenario_file = Path(test_dir) / "scenario-git-assistant.json"
        import json
        scenario_file.write_text(json.dumps(simple_scenario, indent=2))
        
        os.environ["STUB_SCENARIO"] = str(scenario_file)
        os.environ["STUB_STEP"] = "0"
        
        # Create a custom config
        config_content = {
            "kickoff_prompt": "Begin test",
            "roles": {
                "implementer": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True},
                "senior_implementer": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True},
                
                "senior_debugger": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True},
                "git": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True},
                "tester": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True},
                "reviewer": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True},
                "designer": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True}
            },
            "limits": {
                "senior_debugger_max": 3,
                "designer_max": 2,
                "phase_max_executions": 15
            }
        }
        
        config_file = Path(test_dir) / ".ai-run.json"
        config_file.write_text(json.dumps(config_content, indent=2))
        
        # Update project-state.md to start with Git Assistant
        state_file = Path(test_dir) / "project-state.md"
        state_content = state_file.read_text()
        state_content = state_content.replace("Next Role: Implementer", "Next Role: Git Assistant")
        state_file.write_text(state_content)
        
        # Change to test directory
        original_cwd = os.getcwd()
        os.chdir(test_dir)
        
        try:
            # Run ai-run-phase
            print("Running ai-run-phase with Git Assistant...")
            result = subprocess.run(
                [str(ai_platform / "bin" / "ai-run-phase")],
                capture_output=True,
                text=True
            )
            
            print(f"Exit code: {result.returncode}")
            
            # Should exit 0 after Git Assistant completes
            if result.returncode == 0:
                print("✓ ai-run-phase exited 0 when Git Assistant completed")
                
                # Check that phase advanced
                state_content = state_file.read_text()
                if "Active Phase: Phase 11" in state_content:
                    print("✓ Phase correctly advanced")
                else:
                    print("✗ Phase did not advance")
                    return False
            else:
                print("✗ ai-run-phase failed with exit code", result.returncode)
                return False
                
        finally:
            os.chdir(original_cwd)
            
    finally:
        # Cleanup
        shutil.rmtree(test_dir)
        print(f"Cleaned up test directory")
    
    return True


def test_ai_run_cross_phase():
    """Test AC4: ai-run advances pinned phase at Git Assistant completion."""
    print("\n=== Testing AC4: ai-run cross-phase ===")
    
    test_dir, ai_platform = setup_test_directory("Phase 10")
    
    try:
        # Create a scenario that spans two phases
        cross_phase_scenario = [
            {
                "description": "Implementer completes Phase 10",
                "next_role": "Tester",
                "exit_code": 0
            },
            {
                "description": "Tester passes",
                "next_role": "Reviewer",
                "exit_code": 0
            },
            {
                "description": "Reviewer completes",
                "next_role": "Git Assistant",
                "exit_code": 0
            },
            {
                "description": "Git Assistant advances to Phase 11",
                "next_role": "Implementer",
                "active_phase": "Phase 11",
                "exit_code": 0
            },
            {
                "description": "Phase 11 Implementer (should be ordinary, not senior)",
                "next_role": "Tester",
                "exit_code": 0
            },
            {
                "description": "Phase 11 Tester passes",
                "next_role": "Git Assistant",
                "exit_code": 0
            },
            {
                "description": "Phase 11 Git Assistant completes workflow",
                "next_role": "None",
                "exit_code": 0
            }
        ]
        
        # Write scenario file
        scenario_file = Path(test_dir) / "scenario-cross-phase-test.json"
        import json
        scenario_file.write_text(json.dumps(cross_phase_scenario, indent=2))
        
        # Commit the scenario file
        subprocess.run(["git", "add", "scenario-cross-phase-test.json"], cwd=test_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add scenario file"], cwd=test_dir, capture_output=True)
        subprocess.run(["git", "push"], cwd=test_dir, capture_output=True)
        
        os.environ["STUB_SCENARIO"] = str(scenario_file)
        os.environ["STUB_STEP"] = "0"
        
        # Create a custom config
        config_content = {
            "kickoff_prompt": "Begin test",
            "roles": {
                "implementer": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True},
                "senior_implementer": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True},
                
                "senior_debugger": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True},
                "git": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True},
                "tester": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True},
                "reviewer": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True},
                "designer": {"command": [str(ai_platform / "tests" / "stub" / "stub-runner.py")], "kickoff": True}
            },
            "limits": {
                "senior_debugger_max": 3,
                "designer_max": 2,
                "phase_max_executions": 15
            }
        }
        
        config_file = Path(test_dir) / ".ai-run.json"
        config_file.write_text(json.dumps(config_content, indent=2))
        
        # Change to test directory
        original_cwd = os.getcwd()
        os.chdir(test_dir)
        
        try:
            # Run ai-run (not ai-run-phase) - should continue across phases
            print("Running ai-run across phases...")
            result = subprocess.run(
                [str(ai_platform / "bin" / "ai-run")],
                capture_output=True,
                text=True
            )
            
            print(f"Exit code: {result.returncode}")
            print(f"Stderr:\n{result.stderr}")
            print(f"Stdout:\n{result.stdout}")
            
            # ai-run should exit 0 when workflow completes (Git Assistant at end)
            if result.returncode == 0:
                print("✓ ai-run completed successfully across phases")
                
                # Check final state
                state_file = Path("project-state.md")
                state_content = state_file.read_text()
                
                # Should end with None as Next Role (workflow completed)
                if "Next Role: None" in state_content:
                    print("✓ Ended with None (workflow completed) as expected")
                else:
                    print("✗ Didn't end with None")
                    print(f"State content:\n{state_content}")
                    return False
                
                # Check .ai-run-state.json counters
                state_json_file = Path(".ai-run-state.json")
                if state_json_file.exists():
                    state_json = json.loads(state_json_file.read_text())
                    
                    # Check phase is Phase 11
                    if state_json.get("phase") == "Phase 11":
                        print(f"✓ Runtime state phase is Phase 11")
                    else:
                        print(f"✗ Runtime state phase is {state_json.get('phase')}, expected Phase 11")
                        return False
                    
                    # Check implementer counter - should be 1 (not 2) because
                    # Phase 11 implementer should be ordinary, not senior
                    implementer_count = state_json["counters"].get("implementer", 0)
                    if implementer_count == 1:
                        print(f"✓ Implementer counter is 1 (ordinary tier in Phase 11)")
                    else:
                        print(f"✗ Implementer counter is {implementer_count}, expected 1")
                        return False
                else:
                    print("✗ .ai-run-state.json not found")
                    return False
            else:
                print("✗ ai-run failed with exit code", result.returncode)
                print(f"Stdout:\n{result.stdout}")
                return False
                
        finally:
            os.chdir(original_cwd)
            
    finally:
        # Cleanup
        shutil.rmtree(test_dir)
        print(f"Cleaned up test directory")
    
    return True


def main():
    """Run all Phase 10 tests."""
    print("Running Phase 10 acceptance tests...")
    
    tests_passed = True
    
    # Test 1: Mid-phase Active Phase edit
    if not test_midphase_active_phase_edit():
        tests_passed = False
    
    # Test 2: Git Assistant completion
    if not test_git_assistant_completion():
        tests_passed = False
    
    # Test 3: ai-run cross-phase
    if not test_ai_run_cross_phase():
        tests_passed = False
    
    if tests_passed:
        print("\n✓ All Phase 10 tests passed!")
        return 0
    else:
        print("\n✗ Some Phase 10 tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())