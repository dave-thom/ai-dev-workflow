"""Invariant validation for contradictory workflow state (§22)."""

from airun.state import ProjectState
from airun.errors import StopRequired

R1_DESC = "Implementation completed but untested while returning to Implementer"
R2_DESC = "Next Role is Reviewer but QA is not a pass state"
R3_DESC = "Next Role is Git Assistant but Review is not an approval state"
R4_DESC = "Active Phase changed by non-Git-Assistant role"

IMPLEMENTER_TIERS = {"implementer", "senior_implementer"}
QA_PASS_STATES = {"pass", "passed"}
REVIEW_APPROVAL_STATES = {"pass", "passed", "approved"}


def check_invariants(
    original_state: ProjectState,
    new_state: ProjectState,
    logical_role: str,
    limits: dict,
) -> None:
    """
    Check post-execution project-state.md for contradictory state (§22).

    Raises StopRequired with rule §22 if a contradiction is detected.
    """
    violations = []

    # R1: Implementation completed, QA not started, Next Role is Implementer tier
    if (_normalize(new_state.implementation) == "completed"
            and _normalize(new_state.qa) == "not_started"
            and _normalize(new_state.next_role) in IMPLEMENTER_TIERS):
        violations.append(
            f"R1: {R1_DESC} "
            f"(Implementation={new_state.implementation}, "
            f"QA={new_state.qa}, "
            f"Next Role={new_state.next_role})"
        )

    # R2: Next Role Reviewer while QA is not a pass state
    if (_normalize(new_state.next_role) == "reviewer"
            and _normalize(new_state.qa) not in QA_PASS_STATES):
        violations.append(
            f"R2: {R2_DESC} "
            f"(Next Role={new_state.next_role}, "
            f"QA={new_state.qa})"
        )

    # R3: Next Role Git Assistant while Review is not an approval state
    if (_is_git_assistant(new_state.next_role)
            and _normalize(new_state.review) not in REVIEW_APPROVAL_STATES):
        violations.append(
            f"R3: {R3_DESC} "
            f"(Next Role={new_state.next_role}, "
            f"Review={new_state.review})"
        )

    # R4: Active Phase changed by any role other than Git Assistant
    check_phase_change = limits.get("check_phase_change", True)
    if check_phase_change:
        if (original_state.active_phase != new_state.active_phase
                and not _is_git_assistant(logical_role)):
            violations.append(
                f"R4: {R4_DESC} "
                f"(old={original_state.active_phase}, "
                f"new={new_state.active_phase}, "
                f"role={logical_role})"
            )

    if violations:
        detail = "; ".join(violations)
        raise StopRequired(
            f"Contradictory workflow state detected: {detail}",
            rule="§22",
        )


def _normalize(value: str) -> str:
    return value.lower().strip() if value else ""


def _is_git_assistant(role: str) -> bool:
    normalized = _normalize(role)
    return normalized in ("git assistant", "git")