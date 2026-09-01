#!/usr/bin/env python3
"""Test script for Phase 8c acceptance criteria."""

import json
import os
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def setup_test_directory(active_phase="Phase 8c", next_role="Implementer"):
    """Create a temporary directory for testing."""
    test_dir = tempfile.mkdtemp(prefix="ai-run-test-")
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

Name: Test Project

---

## Workflow

Status: In Progress

Active Phase: {active_phase}

Current Role: Implementer

Next Role: {next_role}

Next Action: Test Phase 8c implementation

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


def _write_config(test_dir, ai_platform):
    """Write .ai-run.json pointing all runners at the stub runner."""
    stub = str(ai_platform / "tests" / "stub" / "stub-runner.py")
    config_content = {
        "kickoff_prompt": "Begin test",
        "roles": {
            "implementer": {"command": [stub]},
            "senior_implementer": {"command": [stub]},
            "debugger": {"command": [stub]},
            "senior_debugger": {"command": [stub]},
            "git": {"command": [stub]},
            "tester": {"command": [stub]},
            "reviewer": {"command": [stub]},
            "designer": {"command": [stub]},
        },
        "limits": {
            "senior_debugger_max": 3,
            "designer_max": 2,
            "phase_max_executions": 15,
        },
    }
    (Path(test_dir) / ".ai-run.json").write_text(json.dumps(config_content, indent=2))


def _run_orch(command, scenario_name, test_dir, ai_platform):
    """Run an orchestrator command with a given stub scenario."""
    scenario_file = ai_platform / "tests" / "stub" / (scenario_name + ".json")
    orig_step = os.environ.get("STUB_STEP")
    orig_scenario = os.environ.get("STUB_SCENARIO")

    try:
        os.environ["STUB_SCENARIO"] = str(scenario_file)
        os.environ["STUB_STEP"] = "0"

        orig_cwd = os.getcwd()
        os.chdir(test_dir)
        try:
            return subprocess.run(
                [str(ai_platform / "bin" / command)],
                capture_output=True, text=True,
            )
        finally:
            os.chdir(orig_cwd)
    finally:
        if orig_step is not None:
            os.environ["STUB_STEP"] = orig_step
        else:
            os.environ.pop("STUB_STEP", None)
        if orig_scenario is not None:
            os.environ["STUB_SCENARIO"] = orig_scenario
        else:
            os.environ.pop("STUB_SCENARIO", None)


def _read_state(test_dir):
    """Read .ai-run-state.json from the test directory."""
    return json.loads((Path(test_dir) / ".ai-run-state.json").read_text())


def test_architect_stop():
    """AC 1: Architect stops both ai-run-phase and ai-run, launches no further runner."""
    print("\n=== AC 1: Architect Stop ===")

    for command in ("ai-run-phase", "ai-run"):
        test_dir, ai_platform = setup_test_directory("Phase 8c")
        _write_config(test_dir, ai_platform)

        try:
            result = _run_orch(command, "scenario-architect-stop", test_dir, ai_platform)
            print(f"[{command}] Exit: {result.returncode}")
            if result.stderr:
                print(result.stderr)

            assert result.returncode == 2, f"[{command}] Expected 2, got {result.returncode}"

            output = result.stdout + result.stderr
            assert "\u00a7" + "12" in output, \
                f"[{command}] Expected section-12 rule, got: {output[:200]}"

            state = _read_state(test_dir)
            assert state["counters"]["implementer"] == 1, \
                f"[{command}] implementer counter expected 1, got {state['counters']['implementer']}"
            assert state["total_runs"] == 1, \
                f"[{command}] total_runs expected 1, got {state['total_runs']}"

            print(f"[{command}] PASS")
        finally:
            shutil.rmtree(test_dir)

    print("PASS")
    return True


def test_human_intervention_stop():
    """AC 2: Human intervention stops both ai-run-phase and ai-run with exit 2, rule S13."""
    print("\n=== AC 2: Human Intervention Stop ===")

    for command in ("ai-run-phase", "ai-run"):
        test_dir, ai_platform = setup_test_directory("Phase 8c")
        _write_config(test_dir, ai_platform)

        try:
            result = _run_orch(command, "scenario-human-intervention-stop", test_dir, ai_platform)
            print(f"[{command}] Exit: {result.returncode}")
            if result.stderr:
                print(result.stderr)

            assert result.returncode == 2, f"[{command}] Expected 2, got {result.returncode}"

            output = result.stdout + result.stderr
            assert "\u00a7" + "13" in output, \
                f"[{command}] Expected section-13 rule, got: {output[:200]}"

            state = _read_state(test_dir)
            assert state["counters"]["implementer"] == 1, \
                f"[{command}] implementer counter expected 1, got {state['counters']['implementer']}"
            assert state["total_runs"] == 1, \
                f"[{command}] total_runs expected 1, got {state['total_runs']}"

            print(f"[{command}] PASS")
        finally:
            shutil.rmtree(test_dir)

    print("PASS")
    return True


def test_runner_failure_stop():
    """AC 3: Non-zero runner exit stops both ai-run-phase and ai-run with exit 3."""
    print("\n=== AC 3: Runner Failure Stop ===")

    for command in ("ai-run-phase", "ai-run"):
        test_dir, ai_platform = setup_test_directory("Phase 8c")
        _write_config(test_dir, ai_platform)

        try:
            result = _run_orch(command, "scenario-runner-failure", test_dir, ai_platform)
            print(f"[{command}] Exit: {result.returncode}")
            if result.stderr:
                print(result.stderr)

            assert result.returncode == 3, f"[{command}] Expected 3, got {result.returncode}"

            output = result.stdout + result.stderr
            assert "Runtime failure" in output, \
                f"[{command}] Expected runtime failure message, got: {output[:200]}"

            state = _read_state(test_dir)
            assert state["counters"]["implementer"] == 1, \
                f"[{command}] implementer counter expected 1, got {state['counters']['implementer']}"
            assert state["total_runs"] == 1, \
                f"[{command}] total_runs expected 1, got {state['total_runs']}"

            print(f"[{command}] PASS")
        finally:
            shutil.rmtree(test_dir)

    print("PASS")
    return True


def main():
    """Run Phase 8c acceptance tests."""
    print("Running Phase 8c acceptance tests...")

    passed = True

    if not test_architect_stop():
        passed = False
    if not test_human_intervention_stop():
        passed = False
    if not test_runner_failure_stop():
        passed = False

    if passed:
        print("\nAll Phase 8c tests passed!")
        return 0
    else:
        print("\nSome Phase 8c tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())