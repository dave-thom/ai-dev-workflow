"""Unit tests for airun.invariants module."""

import unittest

from airun.errors import StopRequired
from airun.invariants import check_invariants
from airun.state import ProjectState


class TestInvariants(unittest.TestCase):
    """Test post-execution invariant checks (§22)."""

    def _create_state(self, **kwargs):
        """Create a ProjectState with default values, overriding as needed."""
        defaults = {
            "name": "Test Project",
            "status": "In Progress",
            "active_phase": "Phase 1",
            "current_role": "Implementer",
            "next_role": "Tester",
            "next_action": "Test Phase 1",
            "branch": "main",
            "implementation": "COMPLETED",
            "qa": "NOT_STARTED",
            "review": "NOT_STARTED",
            "human_intervention": False,
            "reason": "None",
            "raw": {},
        }
        defaults.update(kwargs)
        return ProjectState(**defaults)

    def _check(self, state, logical_role="implementer"):
        check_invariants(state, state, logical_role, {})

    def test_valid_handoff_passes(self):
        """A clean Implementer -> Tester handoff raises nothing."""
        self._check(self._create_state(next_role="Tester"))

    def test_r5_annotated_role_stops(self):
        """A Next Role carrying a phase annotation is rejected as unroutable."""
        state = self._create_state(next_role="Implementer (Phase 20.0b)")
        with self.assertRaises(StopRequired) as ctx:
            self._check(state)
        self.assertEqual(ctx.exception.rule, "§22")
        self.assertIn("R5", str(ctx.exception))

    def test_r5_unknown_role_stops(self):
        """A Next Role naming no known role is rejected."""
        state = self._create_state(next_role="Nonsense")
        with self.assertRaises(StopRequired) as ctx:
            self._check(state)
        self.assertIn("R5", str(ctx.exception))

    def test_r5_accepts_every_routable_role(self):
        """Each role the router can resolve, and the idle values, pass R5."""
        roles = [
            "Architect", "Implementer", "Senior Implementer", "UI Designer",
            "Designer", "Tester", "Debugger", "Reviewer", "Git Assistant",
            "Git", "None",
        ]
        for role in roles:
            with self.subTest(role=role):
                # QA/Review set to pass states so only R5 can fire here.
                state = self._create_state(
                    next_role=role, qa="PASS", review="APPROVED"
                )
                self._check(state)

    def test_r1_still_fires_for_plain_implementer(self):
        """Implementation completed and untested while returning to Implementer."""
        state = self._create_state(
            next_role="Implementer", implementation="COMPLETED", qa="NOT_STARTED"
        )
        with self.assertRaises(StopRequired) as ctx:
            self._check(state)
        self.assertIn("R1", str(ctx.exception))

    def test_r1_fires_for_senior_implementer_with_space(self):
        """The senior tier is matched however project-state spells it."""
        state = self._create_state(
            next_role="Senior Implementer",
            implementation="COMPLETED",
            qa="NOT_STARTED",
        )
        with self.assertRaises(StopRequired) as ctx:
            self._check(state)
        self.assertIn("R1", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
