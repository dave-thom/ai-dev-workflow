"""Unit tests for airun.routing module."""

import unittest
from airun.routing import Decision, resolve
from airun.state import ProjectState


class TestRoutingEngine(unittest.TestCase):
    """Test the routing engine's decision logic."""
    
    def _create_state(self, **kwargs):
        """Create a ProjectState with default values, overriding as needed."""
        defaults = {
            "name": "Test Project",
            "status": "In Progress",
            "active_phase": "Phase 1",
            "current_role": "PreviousRole",
            "next_role": "Implementer",
            "next_action": "Implement something",
            "branch": "main",
            "implementation": "NOT_STARTED",
            "qa": "NOT_STARTED",
            "review": "NOT_STARTED",
            "human_intervention": False,
            "reason": "None",
            "raw": {}
        }
        defaults.update(kwargs)
        return ProjectState(**defaults)
    
    def _create_counters(self, **kwargs):
        """Create counters dict with default values."""
        defaults = {
            "implementer": 0,
            "senior_implementer": 0,
            "debugger": 0,
            "senior_debugger": 0,
            "tester": 0,
            "reviewer": 0,
            "git": 0,
            "designer": 0,
            "total_runs": 0
        }
        defaults.update(kwargs)
        return defaults
    
    def _create_limits(self):
        """Create standard limits dict."""
        return {
            "senior_debugger_max": 3,
            "designer_max": 2,
            "phase_max_executions": 15
        }
    
    # Test 1: Next Role: Implementer with implementer == 0 resolves to runner implementer.
    def test_implementer_first_call(self):
        state = self._create_state(next_role="Implementer")
        counters = self._create_counters(implementer=0)
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "launch")
        self.assertEqual(decision.logical_role, "implementer")
        self.assertEqual(decision.runner, "implementer")
        self.assertEqual(decision.rule, "")
    
    # Test 2: Next Role: Implementer with implementer == 1 resolves to senior_implementer
    def test_implementer_second_call(self):
        state = self._create_state(next_role="Implementer")
        counters = self._create_counters(implementer=1)
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "launch")
        self.assertEqual(decision.logical_role, "implementer")
        self.assertEqual(decision.runner, "senior_implementer")
        self.assertEqual(decision.rule, "§7")
    
    # Test 3: Next Role: Debugger resolves to senior_debugger (ordinary debugger tier retired)
    def test_debugger_first_call(self):
        state = self._create_state(next_role="Debugger")
        counters = self._create_counters(debugger=0, senior_debugger=0)
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "launch")
        self.assertEqual(decision.logical_role, "debugger")
        self.assertEqual(decision.runner, "senior_debugger")
        self.assertEqual(decision.rule, "§8")
    
    # Test 4: Next Role: Debugger with senior_debugger == 1 also resolves to senior_debugger
    def test_debugger_second_call(self):
        state = self._create_state(next_role="Debugger")
        counters = self._create_counters(debugger=0, senior_debugger=1)
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "launch")
        self.assertEqual(decision.logical_role, "debugger")
        self.assertEqual(decision.runner, "senior_debugger")
        self.assertEqual(decision.rule, "§8")
    
    # Test 5: senior_debugger == 3 with Next Role: Debugger stops with rule §8
    def test_senior_debugger_limit_reached(self):
        state = self._create_state(next_role="Debugger")
        counters = self._create_counters(debugger=0, senior_debugger=3)
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "stop")
        self.assertEqual(decision.logical_role, "debugger")
        self.assertEqual(decision.runner, "")
        self.assertIn("Senior debugger limit reached", decision.reason)
        self.assertEqual(decision.rule, "§8")
    
    # Test 6: Next Role: Architect stops with rule §12, regardless of counters
    def test_architect_stops(self):
        state = self._create_state(next_role="Architect")
        counters = self._create_counters()
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "stop")
        self.assertEqual(decision.logical_role, "architect")
        self.assertEqual(decision.runner, "")
        self.assertEqual(decision.reason, "Architect must never be launched")
        self.assertEqual(decision.rule, "§12")
    
    # Test 7: Human Intervention Required: Yes stops with rule §13
    def test_human_intervention_stops(self):
        state = self._create_state(next_role="Implementer", human_intervention=True)
        counters = self._create_counters()
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "stop")
        self.assertEqual(decision.logical_role, "implementer")
        self.assertEqual(decision.runner, "")
        self.assertEqual(decision.reason, "Human intervention required")
        self.assertEqual(decision.rule, "§13")
    
    # Test 7b: Human intervention stops even when Next Role is Architect
    def test_human_intervention_stops_architect(self):
        state = self._create_state(next_role="Architect", human_intervention=True)
        counters = self._create_counters()
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "stop")
        self.assertEqual(decision.logical_role, "architect")
        self.assertEqual(decision.runner, "")
        self.assertEqual(decision.reason, "Human intervention required")
        self.assertEqual(decision.rule, "§13")
    
    # Test 8: Simple role mappings
    def test_reviewer_resolution(self):
        state = self._create_state(next_role="Reviewer")
        counters = self._create_counters()
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "launch")
        self.assertEqual(decision.logical_role, "reviewer")
        self.assertEqual(decision.runner, "reviewer")
    
    def test_tester_resolution(self):
        state = self._create_state(next_role="Tester")
        counters = self._create_counters()
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "launch")
        self.assertEqual(decision.logical_role, "tester")
        self.assertEqual(decision.runner, "tester")
    
    def test_git_assistant_resolution(self):
        state = self._create_state(next_role="Git Assistant")
        counters = self._create_counters()
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "launch")
        self.assertEqual(decision.logical_role, "git assistant")
        self.assertEqual(decision.runner, "git")
    
    def test_git_resolution(self):
        state = self._create_state(next_role="Git")
        counters = self._create_counters()
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "launch")
        self.assertEqual(decision.logical_role, "git")
        self.assertEqual(decision.runner, "git")
    
    def test_ui_designer_resolution(self):
        state = self._create_state(next_role="UI Designer")
        counters = self._create_counters()
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "launch")
        self.assertEqual(decision.logical_role, "designer")
        self.assertEqual(decision.runner, "designer")
    
    # Test 9: Designer (without "UI") also resolves to designer
    def test_designer_resolution(self):
        state = self._create_state(next_role="Designer")
        counters = self._create_counters()
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "launch")
        self.assertEqual(decision.logical_role, "designer")
        self.assertEqual(decision.runner, "designer")
    
    # Test 10: Next Role: Nonsense stops with rule §22
    def test_unknown_role_stops(self):
        state = self._create_state(next_role="Nonsense")
        counters = self._create_counters()
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "stop")
        self.assertIn("Unknown role", decision.reason)
        self.assertEqual(decision.rule, "§22")
    
    # Test 11: Next Role: None or empty stops as idle
    def test_none_role_stops(self):
        state = self._create_state(next_role="None")
        counters = self._create_counters()
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "stop")
        self.assertEqual(decision.logical_role, "")
        self.assertEqual(decision.reason, "Workflow idle (no next role)")
        self.assertEqual(decision.rule, "§22")
    
    def test_empty_role_stops(self):
        state = self._create_state(next_role="")
        counters = self._create_counters()
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "stop")
        self.assertEqual(decision.logical_role, "")
        self.assertEqual(decision.reason, "Workflow idle (no next role)")
        self.assertEqual(decision.rule, "§22")
    
    # Test 12: total_runs == phase_max_executions stops with rule §20
    def test_phase_max_executions_stops(self):
        state = self._create_state(next_role="Implementer")
        counters = self._create_counters(total_runs=15)
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "stop")
        self.assertEqual(decision.logical_role, "implementer")
        self.assertIn("Phase execution limit reached", decision.reason)
        self.assertEqual(decision.rule, "§20")
    
    # Test 13: Active Phase: None with Next Role: Implementer stops with rule §22
    def test_no_active_phase_stops(self):
        state = self._create_state(next_role="Implementer", active_phase="None")
        counters = self._create_counters()
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "stop")
        self.assertEqual(decision.logical_role, "implementer")
        self.assertIn("No active phase while role", decision.reason)
        self.assertEqual(decision.rule, "§22")
    
    # Test 14: Role matching is case- and whitespace-insensitive
    def test_case_insensitive_matching(self):
        # Test various case variations
        test_cases = [
            ("IMPLEMENTER", "implementer"),
            ("iMpLeMeNtEr", "implementer"),
            ("debugger", "debugger"),
            ("DEBUGGER", "debugger"),
        ]
        
        for input_role, expected_logical in test_cases:
            state = self._create_state(next_role=input_role)
            counters = self._create_counters()
            limits = self._create_limits()
            
            decision = resolve(state, counters, limits)
            self.assertEqual(decision.logical_role, expected_logical)
    
    def test_whitespace_insensitive_matching(self):
        # Test various whitespace variations
        test_cases = [
            ("Git   Assistant", "git assistant"),
            ("  Git Assistant  ", "git assistant"),
            ("UI  Designer", "designer"),
            ("\tUI Designer\n", "designer"),
        ]
        
        for input_role, expected_logical in test_cases:
            state = self._create_state(next_role=input_role)
            counters = self._create_counters()
            limits = self._create_limits()
            
            decision = resolve(state, counters, limits)
            self.assertEqual(decision.logical_role, expected_logical)
    
    # Test 15: Designer limit check
    def test_designer_limit_reached(self):
        state = self._create_state(next_role="Designer")
        counters = self._create_counters(designer=2)
        limits = self._create_limits()
        
        decision = resolve(state, counters, limits)
        
        self.assertEqual(decision.action, "stop")
        self.assertEqual(decision.logical_role, "designer")
        self.assertIn("Designer limit reached", decision.reason)
    
    # Additional edge cases
    def test_implementer_subsequent_calls_all_senior(self):
        # Test that all implementer calls after the first are senior
        for implementer_count in [1, 2, 3, 5, 10]:
            state = self._create_state(next_role="Implementer")
            counters = self._create_counters(implementer=implementer_count)
            limits = self._create_limits()
            
            decision = resolve(state, counters, limits)
            
            self.assertEqual(decision.action, "launch")
            self.assertEqual(decision.logical_role, "implementer")
            self.assertEqual(decision.runner, "senior_implementer")
            self.assertEqual(decision.rule, "§7")
    
    def test_debugger_flow_with_limits(self):
        # Simulate a debugger flow that hits the senior debugger limit
        counters = self._create_counters(debugger=0, senior_debugger=2)
        limits = self._create_limits()
        
        # Third debugger (senior_debugger count 2)
        state = self._create_state(next_role="Debugger")
        decision = resolve(state, counters, limits)
        self.assertEqual(decision.action, "launch")
        self.assertEqual(decision.runner, "senior_debugger")
        
        # Update counters to simulate the launch
        counters["senior_debugger"] = 3
        
        # Fourth debugger - should hit limit
        decision = resolve(state, counters, limits)
        self.assertEqual(decision.action, "stop")
        self.assertEqual(decision.rule, "§8")


if __name__ == "__main__":
    unittest.main()