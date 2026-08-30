"""Unit tests for airun.state module."""

import os
import tempfile
import unittest
from pathlib import Path

from airun.errors import InvalidStateError
from airun.state import ProjectState, read_project_state, progress_snapshot


class TestProjectStateParser(unittest.TestCase):
    """Test reading and parsing project-state.md files."""
    
    def setUp(self):
        self.fixtures_dir = Path(__file__).parent / "fixtures" / "state"
    
    def test_valid_template(self):
        """Test parsing the template project-state.md."""
        path = self.fixtures_dir / "valid-template.md"
        state = read_project_state(str(path))
        
        self.assertEqual(state.name, "Family School Assistant")
        self.assertEqual(state.status, "Awaiting Work")
        self.assertEqual(state.active_phase, "None")
        self.assertEqual(state.current_role, "None")
        self.assertEqual(state.next_role, "Architect")
        self.assertEqual(state.next_action, "Await approved work or requirements for planning")
        self.assertEqual(state.branch, "master")
        self.assertEqual(state.implementation, "NOT_STARTED")
        self.assertEqual(state.qa, "NOT_STARTED")
        self.assertEqual(state.review, "NOT_STARTED")
        self.assertFalse(state.human_intervention)
        self.assertEqual(state.reason, "None")
        
        # Verify raw dict contains all fields
        self.assertIn("Name", state.raw)
        self.assertIn("Next Role", state.raw)
        self.assertIn("Human Intervention Required", state.raw)
    
    def test_human_intervention_yes(self):
        """Test parsing with Human Intervention Required: Yes."""
        path = self.fixtures_dir / "human-intervention-yes.md"
        state = read_project_state(str(path))
        
        self.assertTrue(state.human_intervention)
        self.assertEqual(state.reason, "Missing configuration file")
    
    def test_missing_next_role(self):
        """Test missing Next Role field raises InvalidStateError."""
        path = self.fixtures_dir / "missing-next-role.md"
        
        with self.assertRaises(InvalidStateError) as cm:
            read_project_state(str(path))
        
        error_msg = str(cm.exception)
        self.assertIn("Missing required fields", error_msg)
        self.assertIn("'Next Role'", error_msg)
    
    def test_duplicate_next_role(self):
        """Test duplicate Next Role field raises InvalidStateError."""
        path = self.fixtures_dir / "duplicate-next-role.md"
        
        with self.assertRaises(InvalidStateError) as cm:
            read_project_state(str(path))
        
        error_msg = str(cm.exception)
        self.assertIn("Duplicate field 'Next Role'", error_msg)
        self.assertIn("'Workflow' and 'Something Else'", error_msg)
    
    def test_nonexistent_path(self):
        """Test non-existent path raises InvalidStateError."""
        with self.assertRaises(InvalidStateError) as cm:
            read_project_state("/nonexistent/path/project-state.md")
        
        error_msg = str(cm.exception)
        self.assertIn("Cannot read", error_msg)
        self.assertIn("/nonexistent/path/project-state.md", error_msg)
    
    def test_whitespace_trimming(self):
        """Test leading and trailing whitespace around values is stripped."""
        path = self.fixtures_dir / "whitespace-test.md"
        state = read_project_state(str(path))
        
        # Values should be trimmed
        self.assertEqual(state.name, "Test Project With Spaces")
        self.assertEqual(state.status, "Phase Complete")
        self.assertEqual(state.active_phase, "Phase 2")
        self.assertEqual(state.current_role, "None")
        self.assertEqual(state.next_role, "Implementer")
        self.assertEqual(state.next_action, "Implement the project state parser per myplan.md Phase 2")
        self.assertEqual(state.branch, "main")
        self.assertEqual(state.implementation, "COMPLETE")
        self.assertEqual(state.qa, "PASS")
        self.assertEqual(state.review, "APPROVE")
        self.assertFalse(state.human_intervention)
        self.assertEqual(state.reason, "None")
    
    def test_invalid_human_intervention(self):
        """Test invalid Human Intervention Required value raises InvalidStateError."""
        path = self.fixtures_dir / "invalid-human-intervention.md"
        
        with self.assertRaises(InvalidStateError) as cm:
            read_project_state(str(path))
        
        error_msg = str(cm.exception)
        self.assertIn("Invalid value for 'Human Intervention Required'", error_msg)
        self.assertIn("'Maybe'", error_msg)
        self.assertIn("expected 'Yes' or 'No'", error_msg)
    
    def test_progress_snapshot(self):
        """Test progress_snapshot returns §21 fields."""
        path = self.fixtures_dir / "valid-template.md"
        state = read_project_state(str(path))
        
        snapshot = progress_snapshot(state)
        
        self.assertEqual(snapshot, {
            'human_intervention': 'No',
            'active_phase': 'None',
            'next_role': 'Architect',
        })
        
        # Test with human intervention yes
        path = self.fixtures_dir / "human-intervention-yes.md"
        state = read_project_state(str(path))
        snapshot = progress_snapshot(state)
        
        self.assertEqual(snapshot, {
            'human_intervention': 'Yes',
            'active_phase': 'Phase 2',
            'next_role': 'Implementer',
        })
    
    def test_parses_current_project_state(self):
        """Test parsing the actual project-state.md from the project root."""
        # This is an integration test to ensure the parser works with real data
        project_root = Path(__file__).parent.parent.parent
        state_path = project_root / "project-state.md"
        
        if state_path.exists():
            state = read_project_state(str(state_path))
            # Just verify it parses without errors
            self.assertIsInstance(state, ProjectState)
            self.assertIn(state.next_role, ["Implementer", "Architect", "None", "Tester", 
                                           "Debugger", "Reviewer", "Git Assistant", "UI Designer"])
            
            # Verify human intervention is boolean
            self.assertIsInstance(state.human_intervention, bool)
    
    def test_standard_library_only(self):
        """Verify state.py imports nothing outside the standard library."""
        import airun.state
        import inspect
        
        source = inspect.getsource(airun.state)
        
        # Check for non-standard library imports
        non_stdlib_imports = [
            line for line in source.split('\n') 
            if line.strip().startswith('import ') or line.strip().startswith('from ')
        ]
        
        # Only allowed imports: typing, collections, re, and our own errors module
        for imp in non_stdlib_imports:
            if 'from airun.errors' in imp or 'import airun.errors' in imp:
                continue
            if 'from typing' in imp or 'import typing' in imp:
                continue
            if 'from collections' in imp or 'import collections' in imp:
                continue
            if 'import re' in imp:
                continue
            
            # If we get here, there's an unexpected import
            self.fail(f"Unexpected import in state.py: {imp}")


if __name__ == '__main__':
    unittest.main()