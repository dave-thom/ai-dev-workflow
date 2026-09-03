#!/usr/bin/env python3
"""Test script for Phase 11 acceptance criteria."""

import json
import os
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def setup_test_directory(active_phase="Phase 11"):
    test_dir = tempfile.mkdtemp(prefix="ai-run-phase11-test-")
    print(f"Created test directory: {test_dir}")

    ai_platform = Path(__file__).parent.parent

    state_content = f"""# PROJECT STATE

This file is the authoritative record of where the project is now.

AI agents read it to determine the active workflow state and next action.

Update existing fields in place. Do not append history, findings, rationale, investigation detail, test evidence, implementation summaries, or completed-task narratives.

Detailed information belongs in the referenced role deliverables.

Do not add new fields or sections unless explicitly instructed to change this schema.

---

## Project

Name: Test Project Phase 11

---

## Workflow

Status: In Progress

Active Phase: {active_phase}

Current Role: Implementer

Next Role: Implementer

Next Action: Test Phase 11 implementation

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

    state_json = {
        "schema": 1,
        "phase": active_phase,
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

    state_json_file = Path(test_dir) / ".ai-run-state.json"
    state_json_file.write_text(json.dumps(state_json, indent=2))

    gitignore_content = """.ai-run-state.json
.ai-run.log
.ai-run.json
"""
    (Path(test_dir) / ".gitignore").write_text(gitignore_content)

    subprocess.run(["git", "init", "-b", "main"], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=test_dir, capture_output=True)

    remote_dir = tempfile.mkdtemp(prefix="ai-run-remote-")
    subprocess.run(["git", "init", "--bare"], cwd=remote_dir, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", remote_dir], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=test_dir, capture_output=True)

    return test_dir, ai_platform


def _write_stub_config(test_dir, ai_platform, extra_limits=None):
    stub_runner = str(ai_platform / "tests" / "stub" / "stub-runner.py")
    config = {
        "kickoff_prompt": "Begin test",
        "roles": {
            "implementer": {"command": [stub_runner], "kickoff": True},
            "senior_implementer": {"command": [stub_runner], "kickoff": True},
            
            "senior_debugger": {"command": [stub_runner], "kickoff": True},
            "git": {"command": [stub_runner], "kickoff": True},
            "tester": {"command": [stub_runner], "kickoff": True},
            "reviewer": {"command": [stub_runner], "kickoff": True},
            "designer": {"command": [stub_runner], "kickoff": True}
        },
        "limits": {
            "senior_debugger_max": 3,
            "designer_max": 2,
            "phase_max_executions": 15
        }
    }
    if extra_limits:
        config["limits"].update(extra_limits)

    (Path(test_dir) / ".ai-run.json").write_text(json.dumps(config, indent=2))


def test_r1_implementation_untested():
    """AC1: Implementer sets Implementation=COMPLETED, QA=NOT_STARTED, Next Role=Implementer."""
    print("\n=== AC1: R1 - Implementation completed but untested ===")

    test_dir, ai_platform = setup_test_directory("Phase 11")

    try:
        _write_stub_config(test_dir, ai_platform)

        scenario_file = ai_platform / "tests" / "stub" / "scenario-phase11-r1.json"
        os.environ["STUB_SCENARIO"] = str(scenario_file)
        os.environ["STUB_STEP"] = "0"

        original_cwd = os.getcwd()
        os.chdir(test_dir)

        try:
            result = subprocess.run(
                [str(ai_platform / "bin" / "ai-next")],
                capture_output=True,
                text=True
            )
            print(f"Exit code: {result.returncode}")
            print(f"Stderr: {result.stderr}")

            if result.returncode == 2 and "§22" in result.stderr:
                print("✓ R1 correctly stopped with exit 2 and rule §22")
                return True
            else:
                print(f"✗ Expected exit 2 with §22, got {result.returncode}")
                print(f"Stderr:\n{result.stderr}")
                print(f"Stdout:\n{result.stdout}")
                return False
        finally:
            os.chdir(original_cwd)
    finally:
        shutil.rmtree(test_dir)
        print(f"Cleaned up test directory")


def test_r2_reviewer_without_qa_pass():
    """AC2: Hand to Reviewer while QA is not pass."""
    print("\n=== AC2: R2 - Reviewer without QA pass ===")

    test_dir, ai_platform = setup_test_directory("Phase 11")

    try:
        state_file = Path(test_dir) / "project-state.md"
        content = state_file.read_text()
        content = content.replace("Next Role: Implementer", "Next Role: Tester")
        state_file.write_text(content)
        subprocess.run(["git", "add", "project-state.md"], cwd=test_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Set Next Role to Tester"], cwd=test_dir, capture_output=True)
        subprocess.run(["git", "push"], cwd=test_dir, capture_output=True)

        _write_stub_config(test_dir, ai_platform)

        scenario_file = ai_platform / "tests" / "stub" / "scenario-phase11-r2.json"
        os.environ["STUB_SCENARIO"] = str(scenario_file)
        os.environ["STUB_STEP"] = "0"

        original_cwd = os.getcwd()
        os.chdir(test_dir)

        try:
            result = subprocess.run(
                [str(ai_platform / "bin" / "ai-next")],
                capture_output=True,
                text=True
            )
            print(f"Exit code: {result.returncode}")
            print(f"Stderr: {result.stderr}")

            if result.returncode == 2 and "§22" in result.stderr:
                print("✓ R2 correctly stopped with exit 2 and rule §22")
                return True
            else:
                print(f"✗ Expected exit 2 with §22, got {result.returncode}")
                print(f"Stderr:\n{result.stderr}")
                print(f"Stdout:\n{result.stdout}")
                return False
        finally:
            os.chdir(original_cwd)
    finally:
        shutil.rmtree(test_dir)
        print(f"Cleaned up test directory")


def test_r3_git_without_review_approval():
    """AC3: Hand to Git Assistant without review approval."""
    print("\n=== AC3: R3 - Git Assistant without review approval ===")

    test_dir, ai_platform = setup_test_directory("Phase 11")

    try:
        state_file = Path(test_dir) / "project-state.md"
        content = state_file.read_text()
        content = content.replace("Next Role: Implementer", "Next Role: Reviewer")
        state_file.write_text(content)
        subprocess.run(["git", "add", "project-state.md"], cwd=test_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Set Next Role to Reviewer"], cwd=test_dir, capture_output=True)
        subprocess.run(["git", "push"], cwd=test_dir, capture_output=True)

        _write_stub_config(test_dir, ai_platform)

        scenario_file = ai_platform / "tests" / "stub" / "scenario-phase11-r3.json"
        os.environ["STUB_SCENARIO"] = str(scenario_file)
        os.environ["STUB_STEP"] = "0"

        original_cwd = os.getcwd()
        os.chdir(test_dir)

        try:
            result = subprocess.run(
                [str(ai_platform / "bin" / "ai-next")],
                capture_output=True,
                text=True
            )
            print(f"Exit code: {result.returncode}")
            print(f"Stderr: {result.stderr}")

            if result.returncode == 2 and "§22" in result.stderr:
                print("✓ R3 correctly stopped with exit 2 and rule §22")
                return True
            else:
                print(f"✗ Expected exit 2 with §22, got {result.returncode}")
                print(f"Stderr:\n{result.stderr}")
                print(f"Stdout:\n{result.stdout}")
                return False
        finally:
            os.chdir(original_cwd)
    finally:
        shutil.rmtree(test_dir)
        print(f"Cleaned up test directory")


def test_r4_phase_change_by_non_git():
    """AC4: Implementer changes Active Phase (R4 enabled)."""
    print("\n=== AC4: R4 - Phase change by non-Git-Assistant ===")

    test_dir, ai_platform = setup_test_directory("Phase 11")

    try:
        _write_stub_config(test_dir, ai_platform)

        scenario_file = ai_platform / "tests" / "stub" / "scenario-phase11-r4.json"
        os.environ["STUB_SCENARIO"] = str(scenario_file)
        os.environ["STUB_STEP"] = "0"

        original_cwd = os.getcwd()
        os.chdir(test_dir)

        try:
            result = subprocess.run(
                [str(ai_platform / "bin" / "ai-next")],
                capture_output=True,
                text=True
            )
            print(f"Exit code: {result.returncode}")
            print(f"Stderr: {result.stderr}")

            if result.returncode == 2 and "§22" in result.stderr:
                print("✓ R4 correctly stopped with exit 2 and rule §22")
                return True
            else:
                print(f"✗ Expected exit 2 with §22, got {result.returncode}")
                print(f"Stderr:\n{result.stderr}")
                print(f"Stdout:\n{result.stdout}")
                return False
        finally:
            os.chdir(original_cwd)
    finally:
        shutil.rmtree(test_dir)
        print(f"Cleaned up test directory")


def test_r4_disabled_phase_change():
    """AC4: Implementer changes Active Phase with R4 disabled — should not stop."""
    print("\n=== AC4: R4 disabled — phase change allowed ===")

    test_dir, ai_platform = setup_test_directory("Phase 11")

    try:
        _write_stub_config(test_dir, ai_platform, {"check_phase_change": False})

        scenario_file = ai_platform / "tests" / "stub" / "scenario-phase11-r4-disabled.json"
        os.environ["STUB_SCENARIO"] = str(scenario_file)
        os.environ["STUB_STEP"] = "0"

        original_cwd = os.getcwd()
        os.chdir(test_dir)

        try:
            result = subprocess.run(
                [str(ai_platform / "bin" / "ai-next")],
                capture_output=True,
                text=True
            )
            print(f"Exit code: {result.returncode}")
            print(f"Stderr: {result.stderr}")

            if result.returncode == 0:
                print("✓ R4 disabled: execution succeeded without stop")
                return True
            else:
                print(f"✗ Expected exit 0, got {result.returncode}")
                print(f"Stderr:\n{result.stderr}")
                print(f"Stdout:\n{result.stdout}")
                return False
        finally:
            os.chdir(original_cwd)
    finally:
        shutil.rmtree(test_dir)
        print(f"Cleaned up test directory")


def test_ac5_full_normal_path():
    """AC5: scenario-implementer-to-git triggers no rule, exits 0 with total_runs==6."""
    print("\n=== AC5: Full normal path — no invariant violations ===")

    test_dir, ai_platform = setup_test_directory("Phase 11")
    initial_phase = "Phase 11"

    try:
        _write_stub_config(test_dir, ai_platform)

        scenario_file = ai_platform / "tests" / "stub" / "scenario-implementer-to-git.json"
        os.environ["STUB_SCENARIO"] = str(scenario_file)
        os.environ["STUB_STEP"] = "0"

        original_cwd = os.getcwd()
        os.chdir(test_dir)

        try:
            result = subprocess.run(
                [str(ai_platform / "bin" / "ai-run-phase")],
                capture_output=True,
                text=True
            )
            print(f"Exit code: {result.returncode}")
            print(f"Stderr:\n{result.stderr}")

            if result.returncode != 0:
                print(f"✗ Expected exit 0, got {result.returncode}")
                print(f"Stdout:\n{result.stdout}")
                return False

            state_json_file = Path(".ai-run-state.json")
            if state_json_file.exists():
                state_json = json.loads(state_json_file.read_text())
                total_runs = state_json.get("total_runs", 0)
                if total_runs == 6:
                    print(f"✓ Total runs correct: {total_runs}")
                    return True
                else:
                    print(f"✗ Total runs incorrect: {total_runs}, expected 6")
                    return False
            else:
                print("✗ .ai-run-state.json not found")
                return False
        finally:
            os.chdir(original_cwd)
    finally:
        shutil.rmtree(test_dir)
        print(f"Cleaned up test directory")


def test_ac6_existing_tests_still_pass():
    """AC6: Phase 8b and 8c scenarios continue to pass unchanged."""
    print("\n=== AC6: Existing Phase 8b/8c tests unchanged ===")

    ai_platform = Path(__file__).parent.parent
    original_cwd = os.getcwd()

    tests_passed = True

    for test_file in ["test_phase8b.py", "test_phase8c.py"]:
        test_path = ai_platform / "tests" / test_file
        print(f"\nRunning {test_file}...")
        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=True,
            text=True,
            timeout=60
        )
        print(f"Exit code: {result.returncode}")
        if result.returncode != 0:
            tests_passed = False
            print(f"Stdout:\n{result.stdout}")
            print(f"Stderr:\n{result.stderr}")
        else:
            print(f"✓ {test_file} passed")

    if tests_passed:
        print("✓ All existing tests pass unchanged")
    else:
        print("✗ Some existing tests failed")

    return tests_passed


def main():
    print("Running Phase 11 acceptance tests...")

    tests_passed = True

    if not test_r1_implementation_untested():
        tests_passed = False

    if not test_r2_reviewer_without_qa_pass():
        tests_passed = False

    if not test_r3_git_without_review_approval():
        tests_passed = False

    if not test_r4_phase_change_by_non_git():
        tests_passed = False

    if not test_r4_disabled_phase_change():
        tests_passed = False

    if not test_ac5_full_normal_path():
        tests_passed = False

    if not test_ac6_existing_tests_still_pass():
        tests_passed = False

    if tests_passed:
        print("\n✓ All Phase 11 tests passed!")
        return 0
    else:
        print("\n✗ Some Phase 11 tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())