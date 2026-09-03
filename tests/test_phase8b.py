#!/usr/bin/env python3
"""Test script for Phase 8b acceptance criteria."""

import json
import os
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def setup_test_directory(active_phase="Phase 8", next_role="Implementer"):
    """Create a temporary directory for testing."""
    test_dir = tempfile.mkdtemp(prefix="ai-run-test-")
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

Name: Test Project

---

## Workflow

Status: In Progress

Active Phase: {active_phase}

Current Role: Implementer

Next Role: {next_role}

Next Action: Test Phase 8b implementation

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


def _write_config(test_dir, ai_platform):
    """Write .ai-run.json pointing all runners at the stub runner."""
    stub = str(ai_platform / "tests" / "stub" / "stub-runner.py")
    config_content = {
        "kickoff_prompt": "Begin test",
        "roles": {
            "implementer": {"command": [stub]},
            "senior_implementer": {"command": [stub]},
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


def test_phase_boundary():
    """AC 1: ai-run-phase exits 0 on phase change, total_runs == 3."""
    print("\n=== AC 1: Phase Boundary ===")

    test_dir, ai_platform = setup_test_directory("Phase 8")
    _write_config(test_dir, ai_platform)

    try:
        result = _run_orch("ai-run-phase", "scenario-phase-boundary", test_dir, ai_platform)
        print(f"Exit: {result.returncode}")
        if result.stderr:
            print(result.stderr)

        assert result.returncode == 0, f"Expected 0, got {result.returncode}"

        state = _read_state(test_dir)
        assert state["total_runs"] == 3, f"total_runs expected 3, got {state['total_runs']}"

        md = (Path(test_dir) / "project-state.md").read_text()
        assert "Active Phase: Phase 9" in md, "Phase did not advance"

        print("PASS")
        return True
    finally:
        shutil.rmtree(test_dir)


def test_cross_phase():
    """AC 2: ai-run across phases resets counters, second implementer is not senior."""
    print("\n=== AC 2: Cross-Phase ===")

    test_dir, ai_platform = setup_test_directory("Phase 8B")
    _write_config(test_dir, ai_platform)

    try:
        result = _run_orch("ai-run", "scenario-cross-phase", test_dir, ai_platform)
        print(f"Exit: {result.returncode}")
        if result.stderr:
            print(result.stderr)

        assert result.returncode == 0, f"Expected 0, got {result.returncode}"

        state = _read_state(test_dir)
        print(json.dumps(state, indent=2))

        assert state["phase"] == "Phase 9", f"phase expected Phase 9, got {state['phase']}"
        assert state["counters"]["implementer"] == 1, \
            f"implementer expected 1, got {state['counters']['implementer']}"
        assert state["counters"]["senior_implementer"] == 0, \
            f"senior_implementer expected 0, got {state['counters']['senior_implementer']}"
        assert state["total_runs"] == 3, \
            f"total_runs expected 3 (Phase 9 only), got {state['total_runs']}"

        print("PASS")
        return True
    finally:
        shutil.rmtree(test_dir)


def test_debugger_limit():
    """AC 3: 4 debugger requests -> 3 senior, stops on 4th with S8."""
    print("\n=== AC 3: Debugger Limit ===")

    test_dir, ai_platform = setup_test_directory("Phase 8", "debugger")
    _write_config(test_dir, ai_platform)

    try:
        result = _run_orch("ai-run-phase", "scenario-debugger-limit", test_dir, ai_platform)
        print(f"Exit: {result.returncode}")
        if result.stderr:
            print(result.stderr)

        assert result.returncode == 2, f"Expected 2, got {result.returncode}"

        output = result.stdout + result.stderr
        assert "\u00a7" + "8" in output, f"Expected section-8 rule, got: {output[:200]}"

        state = _read_state(test_dir)
        print(json.dumps(state, indent=2))

        assert state["counters"]["debugger"] == 0, \
            f"debugger expected 0, got {state['counters']['debugger']}"
        assert state["counters"]["senior_debugger"] == 3, \
            f"senior_debugger expected 3, got {state['counters']['senior_debugger']}"
        assert state["total_runs"] == 3, \
            f"total_runs expected 3, got {state['total_runs']}"

        print("PASS")
        return True
    finally:
        shutil.rmtree(test_dir)


def test_phase_limit():
    """AC 4: 15 executions in one phase, stops before 16th with S20."""
    print("\n=== AC 4: Phase Limit ===")

    test_dir, ai_platform = setup_test_directory("Phase 8")
    _write_config(test_dir, ai_platform)

    try:
        result = _run_orch("ai-run-phase", "scenario-phase-limit", test_dir, ai_platform)
        print(f"Exit: {result.returncode}")
        if result.stderr:
            print(result.stderr)

        assert result.returncode == 2, f"Expected 2, got {result.returncode}"

        output = result.stdout + result.stderr
        assert "\u00a7" + "20" in output, f"Expected section-20 rule, got: {output[:200]}"

        state = _read_state(test_dir)
        print(json.dumps(state, indent=2))

        assert state["total_runs"] == 15, \
            f"total_runs expected 15, got {state['total_runs']}"
        impl_total = state["counters"]["implementer"] + state["counters"]["senior_implementer"]
        assert impl_total == 8, \
            f"implementer total expected 8, got {impl_total}"
        assert state["counters"]["tester"] == 7, \
            f"tester expected 7, got {state['counters']['tester']}"

        print("PASS")
        return True
    finally:
        shutil.rmtree(test_dir)


def main():
    """Run Phase 8b acceptance tests."""
    print("Running Phase 8b acceptance tests...")

    passed = True

    if not test_phase_boundary():
        passed = False
    if not test_cross_phase():
        passed = False
    if not test_debugger_limit():
        passed = False
    if not test_phase_limit():
        passed = False

    if passed:
        print("\nAll Phase 8b tests passed!")
        return 0
    else:
        print("\nSome Phase 8b tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())