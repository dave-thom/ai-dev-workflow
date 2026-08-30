"""Parse project-state.md into an immutable snapshot."""

import re
from collections import defaultdict
from typing import NamedTuple, Dict

from airun.errors import InvalidStateError


class ProjectState(NamedTuple):
    """Immutable snapshot of parsed project-state.md fields."""
    name: str
    status: str
    active_phase: str
    current_role: str
    next_role: str
    next_action: str
    branch: str
    implementation: str
    qa: str
    review: str
    human_intervention: bool
    reason: str
    raw: dict  # every parsed label -> value


def read_project_state(path: str) -> ProjectState:
    """
    Parse project-state.md into a ProjectState.
    
    Raises InvalidStateError if the file cannot be parsed or required fields are missing.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (OSError, IOError) as e:
        raise InvalidStateError(f"Cannot read {path}: {e}")
    
    # Split into sections by "---" lines
    sections = re.split(r'^\s*-{3,}\s*$', content, flags=re.MULTILINE)
    
    # Parse each section
    parsed = {}
    field_to_section = {}
    
    for section in sections:
        if not section.strip():
            continue
        
        # Extract section header (first line after optional leading whitespace)
        lines = section.strip().split('\n')
        if not lines:
            continue
            
        # Check if first line looks like a section header
        first_line = lines[0].strip()
        if not (first_line.startswith('#') or first_line.startswith('##')):
            # This might be the initial description before first section
            continue
            
        # Extract section name (remove # markers)
        section_name = re.sub(r'^#+\s*', '', first_line).strip()
        
        # Parse fields in this section
        for line in lines[1:]:
            line = line.rstrip()
            # Match field: value pattern
            match = re.match(r'^\s*([^:]+?)\s*:\s*(.*?)\s*$', line)
            if match:
                label = match.group(1).strip()
                value = match.group(2).strip()
                
                # Check for duplicate labels
                if label in parsed:
                    raise InvalidStateError(
                        f"Duplicate field '{label}' in sections "
                        f"'{field_to_section[label]}' and '{section_name}'"
                    )
                
                parsed[label] = value
                field_to_section[label] = section_name
    
    # Validate required fields
    required_fields = [
        ('Name', 'Project'),
        ('Status', 'Workflow'),
        ('Active Phase', 'Workflow'),
        ('Current Role', 'Workflow'),
        ('Next Role', 'Workflow'),
        ('Next Action', 'Workflow'),
        ('Branch', 'Git'),
        ('Implementation', 'Execution'),
        ('QA', 'Execution'),
        ('Review', 'Execution'),
        ('Human Intervention Required', 'Escalation'),
        ('Reason', 'Escalation'),
    ]
    
    missing = []
    for field, expected_section in required_fields:
        if field not in parsed:
            missing.append(f"'{field}' (expected in section '{expected_section}')")
    
    if missing:
        raise InvalidStateError(
            f"Missing required fields in {path}: {', '.join(missing)}"
        )
    
    # Parse human intervention as boolean
    human_intervention_raw = parsed['Human Intervention Required'].lower()
    if human_intervention_raw == 'yes':
        human_intervention = True
    elif human_intervention_raw == 'no':
        human_intervention = False
    else:
        raise InvalidStateError(
            f"Invalid value for 'Human Intervention Required': "
            f"'{parsed['Human Intervention Required']}' (expected 'Yes' or 'No')"
        )
    
    # Return structured data
    return ProjectState(
        name=parsed['Name'],
        status=parsed['Status'],
        active_phase=parsed['Active Phase'],
        current_role=parsed['Current Role'],
        next_role=parsed['Next Role'],
        next_action=parsed['Next Action'],
        branch=parsed['Branch'],
        implementation=parsed['Implementation'],
        qa=parsed['QA'],
        review=parsed['Review'],
        human_intervention=human_intervention,
        reason=parsed['Reason'],
        raw=parsed.copy(),
    )


def progress_snapshot(state: ProjectState) -> Dict[str, str]:
    """
    Return the subset of fields used for §21 progress validation.
    
    Returns a dict with keys:
      - human_intervention
      - active_phase  
      - next_role
    """
    return {
        'human_intervention': 'Yes' if state.human_intervention else 'No',
        'active_phase': state.active_phase,
        'next_role': state.next_role,
    }