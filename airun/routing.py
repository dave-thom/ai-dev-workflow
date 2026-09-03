"""Routing engine that maps logical roles to concrete runners with limit checks."""

from typing import NamedTuple, Dict, Any
from airun.state import ProjectState
from airun.errors import StopRequired


class Decision(NamedTuple):
    """Result of resolving a workflow state to an action."""
    action: str          # "launch" | "stop"
    logical_role: str
    runner: str          # "" when stopping
    reason: str
    rule: str            # spec section reference, e.g. "§8"


def resolve(state: ProjectState, counters: Dict[str, int], limits: Dict[str, Any]) -> Decision:
    """
    Resolve the current workflow state to a launch or stop decision.
    
    Applies routing rules in order:
    1. Human intervention always stops (§13)
    2. Architect always stops (§12)
    3. Missing/None Active Phase stops (§22)
    4. Unknown or idle Next Role stops (§22)
    5. Phase max executions limit (§20)
    6. Role-specific limits (senior_debugger_max, designer_max)
    7. Role resolution with tiering logic
    
    Returns a Decision tuple describing the action to take.
    """
    # Normalize the Next Role for consistent matching
    normalized_role = _normalize_role(state.next_role)
    
    # Rule 1: Human intervention always stops (§13)
    if state.human_intervention:
        return Decision(
            action="stop",
            logical_role=normalized_role,
            runner="",
            reason="Human intervention required",
            rule="§13"
        )
    
    # Rule 2: Architect always stops (§12)
    if normalized_role == "architect":
        return Decision(
            action="stop",
            logical_role="architect",
            runner="",
            reason="Architect must never be launched",
            rule="§12"
        )
    
    # Rule 3: Missing/None Active Phase with a non-Architect role stops (§22)
    if (state.active_phase.lower() == "none" or not state.active_phase.strip()) and normalized_role != "architect":
        return Decision(
            action="stop",
            logical_role=normalized_role,
            runner="",
            reason=f"No active phase while role '{state.next_role}' is requested",
            rule="§22"
        )
    
    # Rule 4: Unknown or idle Next Role stops (§22)
    if normalized_role in ["", "none"]:
        return Decision(
            action="stop",
            logical_role="",
            runner="",
            reason="Workflow idle (no next role)",
            rule="§22"
        )
    
    # Get total runs from counters
    total_runs = counters.get("total_runs", 0)
    
    # Rule 5: Phase max executions limit (§20)
    phase_max = limits.get("phase_max_executions", 15)
    if total_runs >= phase_max:
        return Decision(
            action="stop",
            logical_role=normalized_role,
            runner="",
            reason=f"Phase execution limit reached ({total_runs}/{phase_max})",
            rule="§20"
        )
    
    # Role resolution with limit checks
    # Check role-specific limits before resolving the runner
    
    # UI Designer/Designer resolution with limit check
    if normalized_role in ["ui designer", "designer"]:
        logical = "designer"  # Both "UI Designer" and "Designer" map to logical role "designer"
        designer_count = counters.get("designer", 0)
        designer_max = limits.get("designer_max", 2)
        
        if designer_count >= designer_max:
            return Decision(
                action="stop",
                logical_role=logical,
                runner="",
                reason=f"Designer limit reached ({designer_count}/{designer_max})",
                rule="§"
            )
        
        return Decision(
            action="launch",
            logical_role=logical,
            runner="designer",
            reason="",
            rule=""
        )
    
    # Implementer resolution with tiering logic (§7)
    if normalized_role == "implementer":
        logical = "implementer"
        implementer_count = counters.get("implementer", 0)
        
        if implementer_count == 0:
            runner = "implementer"
        else:
            runner = "senior_implementer"
        
        return Decision(
            action="launch",
            logical_role=logical,
            runner=runner,
            reason="",
            rule="§7" if implementer_count > 0 else ""
        )
    
    # Debugger resolution - all requests go to senior_debugger with limit checks (§8)
    if normalized_role == "debugger":
        logical = "debugger"
        senior_debugger_count = counters.get("senior_debugger", 0)
        senior_debugger_max = limits.get("senior_debugger_max", 3)
        
        # Check senior debugger limit
        if senior_debugger_count >= senior_debugger_max:
            return Decision(
                action="stop",
                logical_role=logical,
                runner="",
                reason=f"Senior debugger limit reached ({senior_debugger_count}/{senior_debugger_max})",
                rule="§8"
            )
        
        return Decision(
            action="launch",
            logical_role=logical,
            runner="senior_debugger",
            reason="",
            rule="§8"
        )
    
    # Simple role mappings
    role_to_runner = {
        "tester": "tester",
        "reviewer": "reviewer",
        "git assistant": "git",
        "git": "git",
    }
    
    if normalized_role in role_to_runner:
        return Decision(
            action="launch",
            logical_role=normalized_role,
            runner=role_to_runner[normalized_role],
            reason="",
            rule=""
        )
    
    # Unknown role (§22)
    return Decision(
        action="stop",
        logical_role=normalized_role,
        runner="",
        reason=f"Unknown role '{state.next_role}'",
        rule="§22"
    )


def _normalize_role(role: str) -> str:
    """Normalize role name for consistent matching."""
    if not role:
        return ""
    
    # Lowercase, strip, and collapse internal whitespace
    normalized = " ".join(role.lower().strip().split())
    return normalized