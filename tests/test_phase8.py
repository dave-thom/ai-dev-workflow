#!/usr/bin/env python3
"""Test script for Phase 8 acceptance criteria."""

import os
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


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


def test_runner_override():
    """Test that project-local .ai-run.json overrides global config (AC10)."""
    print("\n=== Testing runner-override config merge ===")

    import json
    from airun.config import load_config

    ai_platform = Path(__file__).parent.parent

    test_dir = tempfile.mkdtemp(prefix="ai-run-override-")
    try:
        override_content = {
            "roles": {
                "reviewer": {"command": ["tests/stub/stub-runner.py"]}
            },
            "limits": {
                "phase_max_executions": 20
            }
        }
        config_file = Path(test_dir) / ".ai-run.json"
        config_file.write_text(json.dumps(override_content, indent=2))

        original_cwd = os.getcwd()
        os.chdir(test_dir)
        try:
            config = load_config()
            assert "reviewer" in config["roles"], "reviewer role not found in merged config"
            assert config["roles"]["reviewer"]["command"] == ["tests/stub/stub-runner.py"], \
                f"reviewer command override failed: {config['roles']['reviewer']['command']}"
            assert config["limits"]["phase_max_executions"] == 20, \
                f"phase_max_executions override failed: {config['limits']['phase_max_executions']}"
            print("✓ Runner-override config merge works correctly")
        finally:
            os.chdir(original_cwd)
    finally:
        shutil.rmtree(test_dir)
        print("Cleaned up test directory")

    return True


def test_ai_role_dryrun():
    """Test that ai-role with AI_ROLE_DRYRUN=1 works (AC9)."""
    print("\n=== Testing AI_ROLE_DRYRUN=1 ===")

    ai_platform = Path(__file__).parent.parent
    ai_role = ai_platform / "bin" / "ai-role"

    env = os.environ.copy()
    env["AI_PLATFORM"] = str(ai_platform)
    env["AI_ROLE_DRYRUN"] = "1"

    test_cases = [
        ("implementer", "o-dev", "openrouter/deepseek/deepseek-v3.2"),
        ("debugger", "o-debug", "openrouter/deepseek/deepseek-v3.2"),
        ("git", "o-git", "openrouter/deepseek/deepseek-v4-flash"),
    ]

    for role, alias, model in test_cases:
        baseline_file = ai_platform / "tests" / "fixtures" / "ai-role-baseline" / f"{alias}.txt"
        result = subprocess.run(
            [str(ai_role), "opencode", role, "-m", model],
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"✗ ai-role opencode {role} failed: {result.stderr}")
            return False

        if baseline_file.exists():
            expected = baseline_file.read_text()
            if result.stdout != expected:
                print(f"✗ {alias} ({role}) baseline mismatch")
                # Show first difference
                import difflib
                diff = list(difflib.unified_diff(
                    expected.splitlines(keepends=True),
                    result.stdout.splitlines(keepends=True),
                    fromfile='expected',
                    tofile='actual',
                    lineterm=''
                ))
                if diff:
                    print("First difference:")
                    for line in diff[:10]:  # Show first 10 lines of diff
                        print(line)
                return False
            else:
                print(f"✓ {alias} ({role}) baseline matches exactly")
        else:
            print(f"⚠ Baseline file not found for {alias}, checking output shape only")
            lines = result.stdout.splitlines()
            if len(lines) < 2 or lines[0] != "opencode" or lines[1] != "--prompt":
                print(f"✗ ai-role opencode {role} output missing expected markers")
                return False
            print(f"✓ {alias} ({role}) dry-run produced valid output")

    print("✓ All AI_ROLE_DRYRUN tests passed")
    return True


def main():
    """Run all tests."""
    print("Running Phase 8 acceptance tests...")
    
    tests_passed = True
    
    # Test 1: ai-run-phase
    if not test_ai_run_phase():
        tests_passed = False
    
    # Test 2: runner-override config merge
    if not test_runner_override():
        tests_passed = False
    
    # Test 3: AI_ROLE_DRYRUN
    if not test_ai_role_dryrun():
        tests_passed = False
    
    if tests_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())