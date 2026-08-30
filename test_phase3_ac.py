#!/usr/bin/env python3
"""Test Phase 3 acceptance criteria explicitly."""

import os
import sys
import json
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from airun.config import load_config
from airun.runtime import RuntimeState
from airun.errors import InvalidStateError, StopRequired


def test_ac1():
    """Acceptance criterion 1: load_config reads global config."""
    print("Testing AC1: load_config reads global config...")
    
    config = load_config(str(project_root))
    
    # Verify all eight runners
    expected_roles = [
        "implementer", "senior_implementer", "debugger", "senior_debugger",
        "git", "tester", "reviewer", "designer"
    ]
    
    for role in expected_roles:
        assert role in config["roles"], f"Missing role: {role}"
        assert "command" in config["roles"][role], f"Role {role} missing command"
        assert isinstance(config["roles"][role]["command"], list), f"Role {role} command not a list"
        assert len(config["roles"][role]["command"]) > 0, f"Role {role} has empty command"
    
    print("  ✓ AC1 passed")


def test_ac2():
    """Acceptance criterion 2: project-local .ai-run.json merges correctly."""
    print("Testing AC2: project-local config merge...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create global config
        global_config_path = Path(tmpdir) / "config" / "ai-run.json"
        global_config_path.parent.mkdir(parents=True)
        
        global_config = {
            "kickoff_prompt": "Global prompt",
            "roles": {
                "implementer": {"command": ["global-implementer"]},
                "reviewer": {"command": ["global-reviewer"]}
            },
            "limits": {
                "phase_max_executions": 10,
                "senior_debugger_max": 3,
                "designer_max": 2
            }
        }
        
        with open(global_config_path, 'w') as f:
            json.dump(global_config, f)
        
        # Create local override
        local_config = {
            "roles": {
                "reviewer": {"command": ["local-reviewer", "--fast"]}
            },
            "limits": {
                "phase_max_executions": 20
            }
        }
        
        local_config_path = Path(tmpdir) / ".ai-run.json"
        with open(local_config_path, 'w') as f:
            json.dump(local_config, f)
        
        # Change to temp directory and load config
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        
        try:
            config = load_config(tmpdir)
            
            # Verify merged values
            assert config["kickoff_prompt"] == "Global prompt", "Kickoff prompt should be from global"
            assert config["roles"]["reviewer"]["command"] == ["local-reviewer", "--fast"], "Local role should override"
            assert config["roles"]["implementer"]["command"] == ["global-implementer"], "Non-overridden role should stay"
            assert config["limits"]["phase_max_executions"] == 20, "Local limit should override"
            assert config["limits"]["senior_debugger_max"] == 3, "Non-overridden limit should stay"
            
        finally:
            os.chdir(original_cwd)
    
    print("  ✓ AC2 passed")


def test_ac3():
    """Acceptance criterion 3: config with empty command raises InvalidStateError."""
    print("Testing AC3: empty command validation...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config" / "ai-run.json"
        config_path.parent.mkdir(parents=True)
        
        config = {
            "kickoff_prompt": "Test",
            "roles": {
                "implementer": {"command": []}
            },
            "limits": {
                "senior_debugger_max": 3,
                "designer_max": 2,
                "phase_max_executions": 15
            }
        }
        
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        try:
            load_config(tmpdir)
            assert False, "Expected InvalidStateError but none raised"
        except InvalidStateError as e:
            error_msg = str(e)
            assert "command list cannot be empty" in error_msg, f"Wrong error: {error_msg}"
    
    print("  ✓ AC3 passed")


def test_ac4():
    """Acceptance criterion 4: missing .ai-run-state.json initializes counters to zero."""
    print("Testing AC4: missing runtime state file initializes...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / ".ai-run-state.json"
        runtime = RuntimeState(str(state_path))
        
        counters = runtime.load("Phase 1")
        
        # All counters should be 0
        for counter_name, value in counters.items():
            assert value == 0, f"Counter {counter_name} should be 0, got {value}"
        
        assert runtime.get_total_runs() == 0, f"total_runs should be 0, got {runtime.get_total_runs()}"
        assert runtime.get_phase() == "Phase 1", f"Phase should be 'Phase 1', got {runtime.get_phase()}"
    
    print("  ✓ AC4 passed")


def test_ac5():
    """Acceptance criterion 5: state file with matching phase retains counters."""
    print("Testing AC5: matching phase retains counters...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / ".ai-run-state.json"
        
        # Create initial state
        initial_state = {
            "schema": 1,
            "phase": "Phase 13",
            "counters": {
                "implementer": 1,
                "senior_implementer": 0,
                "designer": 0,
                "tester": 3,
                "debugger": 1,
                "senior_debugger": 2,
                "reviewer": 0,
                "git": 0
            },
            "total_runs": 7
        }
        
        with open(state_path, 'w') as f:
            json.dump(initial_state, f)
        
        # Load with same phase
        runtime = RuntimeState(str(state_path))
        counters = runtime.load("Phase 13")
        
        # Should retain counters
        assert counters["implementer"] == 1, f"implementer should be 1, got {counters['implementer']}"
        assert counters["tester"] == 3, f"tester should be 3, got {counters['tester']}"
        assert counters["senior_debugger"] == 2, f"senior_debugger should be 2, got {counters['senior_debugger']}"
        assert runtime.get_total_runs() == 7, f"total_runs should be 7, got {runtime.get_total_runs()}"
        assert runtime.get_phase() == "Phase 13", f"Phase should be 'Phase 13', got {runtime.get_phase()}"
    
    print("  ✓ AC5 passed")


def test_ac6():
    """Acceptance criterion 6: state file with different phase resets counters."""
    print("Testing AC6: different phase resets counters...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / ".ai-run-state.json"
        
        # Create initial state for Phase 5
        initial_state = {
            "schema": 1,
            "phase": "Phase 5",
            "counters": {
                "implementer": 5,
                "senior_implementer": 3,
                "designer": 1,
                "tester": 2,
                "debugger": 2,
                "senior_debugger": 0,
                "reviewer": 1,
                "git": 0
            },
            "total_runs": 14
        }
        
        with open(state_path, 'w') as f:
            json.dump(initial_state, f)
        
        # Load with different phase (Phase 6)
        runtime = RuntimeState(str(state_path))
        counters = runtime.load("Phase 6")
        
        # All counters should be reset to 0
        for counter_name, value in counters.items():
            assert value == 0, f"Counter {counter_name} should be 0 after phase change, got {value}"
        
        assert runtime.get_total_runs() == 0, f"total_runs should be 0 after phase change, got {runtime.get_total_runs()}"
        assert runtime.get_phase() == "Phase 6", f"Phase should be 'Phase 6', got {runtime.get_phase()}"
    
    print("  ✓ AC6 passed")


def test_ac7():
    """Acceptance criterion 7: invalid runtime state raises StopRequired with distinct reasons."""
    print("Testing AC7: invalid runtime state validation...")
    
    test_cases = [
        ("wrong-schema.json", "unsupported schema version", "Wrong schema"),
        ("missing-counters.json", "missing counters key", "Missing counters"),
        ("negative-counter.json", "must be non-negative integer", "Negative counter"),
        ("invalid-total-runs.json", "total_runs (4) less than sum of counters (5)", "Invalid total_runs"),
    ]
    
    for filename, expected_error, description in test_cases:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / ".ai-run-state.json"
            
            # Load fixture
            fixture_path = project_root / "tests" / "fixtures" / "runtime" / filename
            with open(fixture_path, 'r') as f:
                fixture_data = json.load(f)
            
            # Write to temp location
            with open(state_path, 'w') as f:
                json.dump(fixture_data, f)
            
            runtime = RuntimeState(str(state_path))
            
            try:
                runtime.load("Phase 1")
                assert False, f"Expected StopRequired for {description} but none raised"
            except StopRequired as e:
                error_msg = str(e)
                assert expected_error in error_msg, f"Wrong error for {description}: {error_msg}"
    
    print("  ✓ AC7 passed")


def test_ac8():
    """Acceptance criterion 8: save writes atomically and round-trips."""
    print("Testing AC8: atomic save and round-trip...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / ".ai-run-state.json"
        runtime = RuntimeState(str(state_path))
        
        # Load and modify
        runtime.load("Test Phase")
        runtime.increment_counter("implementer")
        runtime.increment_counter("tester")
        runtime.increment_counter("tester")
        runtime.save()
        
        # Verify file exists
        assert state_path.exists(), "State file should exist after save"
        
        # Load and verify content
        with open(state_path, 'r') as f:
            saved_state = json.load(f)
        
        assert saved_state["schema"] == 1
        assert saved_state["phase"] == "Test Phase"
        assert saved_state["counters"]["implementer"] == 1
        assert saved_state["counters"]["tester"] == 2
        assert saved_state["total_runs"] == 3
        
        # Verify atomic save left no temp files
        temp_files = list(state_path.parent.glob(f"{state_path.name}.*"))
        assert len(temp_files) == 0, f"Temp files left after save: {temp_files}"
    
    print("  ✓ AC8 passed")


def main():
    """Run all acceptance criteria tests."""
    print("Running Phase 3 acceptance criteria tests...")
    print("=" * 60)
    
    tests = [
        test_ac1,
        test_ac2,
        test_ac3,
        test_ac4,
        test_ac5,
        test_ac6,
        test_ac7,
        test_ac8,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Summary: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("All Phase 3 acceptance criteria satisfied!")
        return 0
    else:
        print(f"{failed} acceptance criteria failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())