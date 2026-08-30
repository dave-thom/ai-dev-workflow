"""Unit tests for airun.config and airun.runtime modules."""

import os
import json
import tempfile
import unittest
from pathlib import Path

from airun.errors import InvalidStateError, StopRequired
from airun.config import load_config
from airun.runtime import RuntimeState


class TestConfigLoading(unittest.TestCase):
    """Test configuration loading and validation."""
    
    def setUp(self):
        self.fixtures_dir = Path(__file__).parent / "fixtures"
        self.project_root = Path(__file__).parent.parent
    
    def test_load_global_config(self):
        """Test loading the global config/ai-run.json."""
        config = load_config(str(self.project_root))
        
        # Verify structure
        self.assertIn("kickoff_prompt", config)
        self.assertIn("roles", config)
        self.assertIn("limits", config)
        
        # Verify kickoff prompt
        self.assertEqual(
            config["kickoff_prompt"],
            "Begin the workflow defined by project-state.md."
        )
        
        # Verify all roles exist
        expected_roles = [
            "implementer", "senior_implementer", "debugger", "senior_debugger",
            "git", "tester", "reviewer", "designer"
        ]
        for role in expected_roles:
            self.assertIn(role, config["roles"])
            self.assertIn("command", config["roles"][role])
            self.assertIsInstance(config["roles"][role]["command"], list)
            self.assertGreater(len(config["roles"][role]["command"]), 0)
        
        # Verify limits
        self.assertEqual(config["limits"]["senior_debugger_max"], 3)
        self.assertEqual(config["limits"]["designer_max"], 2)
        self.assertEqual(config["limits"]["phase_max_executions"], 15)
    
    def test_load_with_local_override(self):
        """Test loading config with project-local .ai-run.json override."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock global config
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
                "kickoff_prompt": "Local prompt",
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
                self.assertEqual(config["kickoff_prompt"], "Local prompt")
                
                # Overridden role
                self.assertEqual(
                    config["roles"]["reviewer"]["command"],
                    ["local-reviewer", "--fast"]
                )
                
                # Non-overridden role
                self.assertEqual(
                    config["roles"]["implementer"]["command"],
                    ["global-implementer"]
                )
                
                # Overridden limit
                self.assertEqual(config["limits"]["phase_max_executions"], 20)
                
                # Non-overridden limit
                self.assertEqual(config["limits"]["senior_debugger_max"], 3)
                
            finally:
                os.chdir(original_cwd)
    
    def test_missing_required_limit(self):
        """Test config missing required limit raises InvalidStateError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config" / "ai-run.json"
            config_path.parent.mkdir(parents=True)
            
            config = {
                "kickoff_prompt": "Test",
                "roles": {
                    "implementer": {"command": ["test"]}
                },
                "limits": {
                    "senior_debugger_max": 3,
                    "designer_max": 2
                    # Missing phase_max_executions
                }
            }
            
            with open(config_path, 'w') as f:
                json.dump(config, f)
            
            with self.assertRaises(InvalidStateError) as cm:
                load_config(tmpdir)
            
            error_msg = str(cm.exception)
            self.assertIn("phase_max_executions", error_msg)
    
    def test_empty_command_list(self):
        """Test role with empty command list raises InvalidStateError."""
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
            
            with self.assertRaises(InvalidStateError) as cm:
                load_config(tmpdir)
            
            error_msg = str(cm.exception)
            self.assertIn("command list cannot be empty", error_msg)
    
    def test_non_string_command_part(self):
        """Test role command with non-string part raises InvalidStateError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config" / "ai-run.json"
            config_path.parent.mkdir(parents=True)
            
            config = {
                "kickoff_prompt": "Test",
                "roles": {
                    "implementer": {"command": ["cmd", 123]}
                },
                "limits": {
                    "senior_debugger_max": 3,
                    "designer_max": 2,
                    "phase_max_executions": 15
                }
            }
            
            with open(config_path, 'w') as f:
                json.dump(config, f)
            
            with self.assertRaises(InvalidStateError) as cm:
                load_config(tmpdir)
            
            error_msg = str(cm.exception)
            self.assertIn("must be a string", error_msg)


class TestRuntimeState(unittest.TestCase):
    """Test runtime state management (.ai-run-state.json)."""
    
    def setUp(self):
        self.fixtures_dir = Path(__file__).parent / "fixtures" / "runtime"
    
    def test_load_new_file(self):
        """Test loading non-existent file initializes default state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / ".ai-run-state.json"
            runtime = RuntimeState(str(state_path))
            
            counters = runtime.load("Phase 1")
            
            # Verify default counters
            expected_counters = {
                "implementer": 0,
                "senior_implementer": 0,
                "designer": 0,
                "tester": 0,
                "debugger": 0,
                "senior_debugger": 0,
                "reviewer": 0,
                "git": 0
            }
            
            self.assertEqual(counters, expected_counters)
            self.assertEqual(runtime.get_total_runs(), 0)
            self.assertEqual(runtime.get_phase(), "Phase 1")
    
    def test_load_existing_same_phase(self):
        """Test loading existing file with same phase retains counters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / ".ai-run-state.json"
            
            # Create initial state
            initial_state = {
                "schema": 1,
                "phase": "Phase 5",
                "counters": {
                    "implementer": 2,
                    "senior_implementer": 1,
                    "designer": 0,
                    "tester": 3,
                    "debugger": 1,
                    "senior_debugger": 0,
                    "reviewer": 0,
                    "git": 0
                },
                "total_runs": 7
            }
            
            with open(state_path, 'w') as f:
                json.dump(initial_state, f)
            
            # Load with same phase
            runtime = RuntimeState(str(state_path))
            counters = runtime.load("Phase 5")
            
            # Should retain counters
            self.assertEqual(counters["implementer"], 2)
            self.assertEqual(counters["tester"], 3)
            self.assertEqual(runtime.get_total_runs(), 7)
            self.assertEqual(runtime.get_phase(), "Phase 5")
    
    def test_load_existing_different_phase(self):
        """Test loading existing file with different phase resets counters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / ".ai-run-state.json"
            
            # Create initial state for Phase 5
            initial_state = {
                "schema": 1,
                "phase": "Phase 5",
                "counters": {
                    "implementer": 2,
                    "senior_implementer": 1,
                    "designer": 0,
                    "tester": 3,
                    "debugger": 1,
                    "senior_debugger": 0,
                    "reviewer": 0,
                    "git": 0
                },
                "total_runs": 7
            }
            
            with open(state_path, 'w') as f:
                json.dump(initial_state, f)
            
            # Load with different phase (Phase 6)
            runtime = RuntimeState(str(state_path))
            counters = runtime.load("Phase 6")
            
            # Should reset all counters
            self.assertEqual(counters["implementer"], 0)
            self.assertEqual(counters["tester"], 0)
            self.assertEqual(runtime.get_total_runs(), 0)
            self.assertEqual(runtime.get_phase(), "Phase 6")
    
    def test_increment_and_save(self):
        """Test incrementing counters and saving."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / ".ai-run-state.json"
            runtime = RuntimeState(str(state_path))
            
            runtime.load("Phase 1")
            
            # Increment some counters
            runtime.increment_counter("implementer")
            runtime.increment_counter("tester")
            runtime.increment_counter("tester")
            runtime.save()
            
            # Verify in-memory state
            counters = runtime.get_counters()
            self.assertEqual(counters["implementer"], 1)
            self.assertEqual(counters["tester"], 2)
            self.assertEqual(runtime.get_total_runs(), 3)
            
            # Reload and verify persistence
            runtime2 = RuntimeState(str(state_path))
            counters2 = runtime2.load("Phase 1")
            
            self.assertEqual(counters2["implementer"], 1)
            self.assertEqual(counters2["tester"], 2)
            self.assertEqual(runtime2.get_total_runs(), 3)
    
    def test_wrong_schema_raises_stop(self):
        """Test wrong schema version raises StopRequired."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / ".ai-run-state.json"
            
            state = {
                "schema": 2,  # Wrong version
                "phase": "Phase 1",
                "counters": {"implementer": 1},
                "total_runs": 1
            }
            
            with open(state_path, 'w') as f:
                json.dump(state, f)
            
            runtime = RuntimeState(str(state_path))
            
            with self.assertRaises(StopRequired) as cm:
                runtime.load("Phase 1")
            
            error_msg = str(cm.exception)
            self.assertIn("unsupported schema version", error_msg)
            self.assertEqual(cm.exception.rule, "runtime corruption")
    
    def test_missing_counters_raises_stop(self):
        """Test missing counters key raises StopRequired."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / ".ai-run-state.json"
            
            state = {
                "schema": 1,
                "phase": "Phase 1",
                "total_runs": 1
                # Missing counters
            }
            
            with open(state_path, 'w') as f:
                json.dump(state, f)
            
            runtime = RuntimeState(str(state_path))
            
            with self.assertRaises(StopRequired) as cm:
                runtime.load("Phase 1")
            
            error_msg = str(cm.exception)
            self.assertIn("missing counters key", error_msg)
            self.assertEqual(cm.exception.rule, "runtime corruption")
    
    def test_negative_counter_raises_stop(self):
        """Test negative counter raises StopRequired."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / ".ai-run-state.json"
            
            state = {
                "schema": 1,
                "phase": "Phase 1",
                "counters": {
                    "implementer": -1,
                    "senior_implementer": 0,
                    "designer": 0,
                    "tester": 0,
                    "debugger": 0,
                    "senior_debugger": 0,
                    "reviewer": 0,
                    "git": 0
                },
                "total_runs": 1
            }
            
            with open(state_path, 'w') as f:
                json.dump(state, f)
            
            runtime = RuntimeState(str(state_path))
            
            with self.assertRaises(StopRequired) as cm:
                runtime.load("Phase 1")
            
            error_msg = str(cm.exception)
            self.assertIn("must be non-negative integer", error_msg)
            self.assertEqual(cm.exception.rule, "runtime corruption")
    
    def test_invalid_total_runs_raises_stop(self):
        """Test total_runs less than sum of counters raises StopRequired."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / ".ai-run-state.json"
            
            state = {
                "schema": 1,
                "phase": "Phase 1",
                "counters": {
                    "implementer": 3,
                    "senior_implementer": 2,
                    "designer": 0,
                    "tester": 0,
                    "debugger": 0,
                    "senior_debugger": 0,
                    "reviewer": 0,
                    "git": 0
                },
                "total_runs": 4  # Sum of counters is 5
            }
            
            with open(state_path, 'w') as f:
                json.dump(state, f)
            
            runtime = RuntimeState(str(state_path))
            
            with self.assertRaises(StopRequired) as cm:
                runtime.load("Phase 1")
            
            error_msg = str(cm.exception)
            self.assertIn("total_runs (4) less than sum of counters (5)", error_msg)
            self.assertEqual(cm.exception.rule, "runtime corruption")
    
    def test_atomic_save(self):
        """Test save uses atomic rename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / ".ai-run-state.json"
            runtime = RuntimeState(str(state_path))
            
            runtime.load("Phase 1")
            runtime.increment_counter("implementer")
            
            # Monitor the directory
            before_files = set(os.listdir(tmpdir))
            
            runtime.save()
            
            # Should have the main file, no temp files left
            after_files = set(os.listdir(tmpdir))
            self.assertEqual(after_files, {".ai-run-state.json"})
            
            # Verify content
            with open(state_path, 'r') as f:
                saved_state = json.load(f)
            
            self.assertEqual(saved_state["counters"]["implementer"], 1)
            self.assertEqual(saved_state["total_runs"], 1)
    
    def test_missing_counter_added(self):
        """Test missing individual counter is added with default value 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / ".ai-run-state.json"
            
            # State missing some counters
            state = {
                "schema": 1,
                "phase": "Phase 1",
                "counters": {
                    "implementer": 1,
                    "tester": 2
                    # Missing other counters
                },
                "total_runs": 3
            }
            
            with open(state_path, 'w') as f:
                json.dump(state, f)
            
            runtime = RuntimeState(str(state_path))
            counters = runtime.load("Phase 1")
            
            # All counters should be present
            self.assertIn("implementer", counters)
            self.assertIn("tester", counters)
            self.assertIn("debugger", counters)
            self.assertIn("senior_debugger", counters)
            self.assertIn("reviewer", counters)
            self.assertIn("git", counters)
            self.assertIn("designer", counters)
            self.assertIn("senior_implementer", counters)
            
            # Existing values preserved
            self.assertEqual(counters["implementer"], 1)
            self.assertEqual(counters["tester"], 2)
            
            # Missing values default to 0
            self.assertEqual(counters["debugger"], 0)
            self.assertEqual(counters["senior_debugger"], 0)


if __name__ == '__main__':
    unittest.main()