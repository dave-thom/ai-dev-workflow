"""Invariant validation for contradictory workflow state (§22)."""

from airun.state import ProjectState
from airun.errors import StopRequired

R1_DESC = "Implementation completed but untested while returning to Implementer"
R2_DESC = "Next Role is Reviewer but QA is not a pass state"
R3_DESC = "Next Role is Git Assistant but Review is not an approval state"
R4_DESC = "Active Phase changed by non-Git-Assistant role"
R5_DESC = "Next Role is not a recognised workflow role"

IMPLEMENTER_TIERS = {"implementer", "senior implementer", "senior_implementer"}

# Every value the router can resolve, plus the idle values. A Next Role outside
# this set cannot be routed, so it is rejected by the role that wrote it rather
# than stopping the following run with an opaque "unknown role".
VALID_NEXT_ROLES = {
    "architect",
    "implementer",
    "senior implementer",
    "senior_implementer",
    "ui designer",
    "designer",
    "tester",
    "debugger",
    "reviewer",
    "git assistant",
    "git",
    "none",
    "",
}
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

    Rules checked: R5 (unroutable Next Role), R1-R3 (handoffs that contradict
    the Execution fields) and R4 (Active Phase changed by a non-Git-Assistant).

    Raises StopRequired with rule §22 if a contradiction is detected.
    """
    violations = []

    # R5: Next Role is not a routable role name. Checked first: an unrecognised
    # value also defeats the R1-R3 comparisons below.
    if _normalize(new_state.next_role) not in VALID_NEXT_ROLES:
        violations.append(
            f"R5: {R5_DESC} "
            f"(Next Role={new_state.next_role}). "
            f"Next Role must be exactly one role name, with no phase "
            f"annotation or other commentary."
        )

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
    """Lowercase and collapse whitespace, matching routing's role normalisation."""
    if not value:
        return ""
    return " ".join(value.lower().split())


def _is_git_assistant(role: str) -> bool:
    normalized = _normalize(role)
    return normalized in ("git assistant", "git")