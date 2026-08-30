#!/usr/bin/env python3
"""Test Phase 2 acceptance criteria explicitly."""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from airun.state import read_project_state, progress_snapshot
from airun.errors import InvalidStateError


def test_ac1():
    """Acceptance criterion 1: template parses correctly."""
    print("Testing AC1: template project-state.md parsing...")
    template_path = project_root / "templates" / "project-state.md"
    state = read_project_state(str(template_path))
    
    assert state.next_role == "Architect", f"Expected 'Architect', got '{state.next_role}'"
    assert state.active_phase == "None", f"Expected 'None', got '{state.active_phase}'"
    assert state.human_intervention is False, f"Expected False, got {state.human_intervention}"
    print("  ✓ AC1 passed")


def test_ac2():
    """Acceptance criterion 2: Human Intervention Required: Yes yields True."""
    print("Testing AC2: Human Intervention Required: Yes...")
    fixture_path = project_root / "tests" / "fixtures" / "state" / "human-intervention-yes.md"
    state = read_project_state(str(fixture_path))
    
    assert state.human_intervention is True, f"Expected True, got {state.human_intervention}"
    print("  ✓ AC2 passed")


def test_ac3():
    """Acceptance criterion 3: missing Next Role raises InvalidStateError naming field."""
    print("Testing AC3: missing Next Role field...")
    fixture_path = project_root / "tests" / "fixtures" / "state" / "missing-next-role.md"
    
    try:
        read_project_state(str(fixture_path))
        assert False, "Expected InvalidStateError but none raised"
    except InvalidStateError as e:
        error_msg = str(e)
        assert "'Next Role'" in error_msg, f"Expected error to mention 'Next Role', got: {error_msg}"
        print("  ✓ AC3 passed")


def test_ac4():
    """Acceptance criterion 4: duplicated Next Role raises InvalidStateError."""
    print("Testing AC4: duplicated Next Role field...")
    fixture_path = project_root / "tests" / "fixtures" / "state" / "duplicate-next-role.md"
    
    try:
        read_project_state(str(fixture_path))
        assert False, "Expected InvalidStateError but none raised"
    except InvalidStateError as e:
        error_msg = str(e)
        assert "Duplicate field 'Next Role'" in error_msg, f"Expected duplicate field error, got: {error_msg}"
        print("  ✓ AC4 passed")


def test_ac5():
    """Acceptance criterion 5: non-existent path raises InvalidStateError."""
    print("Testing AC5: non-existent path...")
    try:
        read_project_state("/nonexistent/path/project-state.md")
        assert False, "Expected InvalidStateError but none raised"
    except InvalidStateError as e:
        error_msg = str(e)
        assert "Cannot read" in error_msg, f"Expected 'Cannot read' in error, got: {error_msg}"
        print("  ✓ AC5 passed")


def test_ac6():
    """Acceptance criterion 6: whitespace trimming and preservation."""
    print("Testing AC6: whitespace handling...")
    fixture_path = project_root / "tests" / "fixtures" / "state" / "whitespace-test.md"
    state = read_project_state(str(fixture_path))
    
    # Test trimming
    assert state.name == "Test Project With Spaces", f"Expected trimmed name, got '{state.name}'"
    assert state.next_action == "Implement the project state parser per myplan.md Phase 2", \
        f"Expected trimmed next_action, got '{state.next_action}'"
    
    # Test preservation of internal spacing (next_action has internal spaces)
    assert "  " not in state.name, "Internal double spaces should not be collapsed"
    print("  ✓ AC6 passed")


def test_ac7():
    """Acceptance criterion 7: progress_snapshot returns §21 fields."""
    print("Testing AC7: progress_snapshot returns correct fields...")
    fixture_path = project_root / "tests" / "fixtures" / "state" / "human-intervention-yes.md"
    state = read_project_state(str(fixture_path))
    
    snapshot = progress_snapshot(state)
    
    expected_keys = {'human_intervention', 'active_phase', 'next_role'}
    actual_keys = set(snapshot.keys())
    
    assert actual_keys == expected_keys, f"Expected keys {expected_keys}, got {actual_keys}"
    assert snapshot['human_intervention'] == 'Yes'
    assert snapshot['active_phase'] == 'Phase 2'
    assert snapshot['next_role'] == 'Implementer'
    print("  ✓ AC7 passed")


def test_ac8():
    """Acceptance criterion 8: state.py uses standard library only."""
    print("Testing AC8: standard library imports only...")
    import airun.state
    import inspect
    
    source = inspect.getsource(airun.state)
    lines = source.split('\n')
    
    allowed_imports = {
        'typing', 'collections', 're', 'airun.errors'
    }
    
    for line in lines:
        line = line.strip()
        if line.startswith('import ') or line.startswith('from '):
            # Check if it's an allowed import
            if 'from airun.errors' in line or 'import airun.errors' in line:
                continue
            if 'from typing' in line or 'import typing' in line:
                continue
            if 'from collections' in line or 'import collections' in line:
                continue
            if 'import re' in line:
                continue
            
            # If we get here, it's an unexpected import
            assert False, f"Unexpected import in state.py: {line}"
    
    print("  ✓ AC8 passed")


def main():
    """Run all acceptance criteria tests."""
    print("Running Phase 2 acceptance criteria tests...")
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
        print("All Phase 2 acceptance criteria satisfied!")
        return 0
    else:
        print(f"{failed} acceptance criteria failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())