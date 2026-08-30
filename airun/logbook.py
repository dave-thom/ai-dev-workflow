"""Logbook for orchestrator events."""

import time
from typing import Optional
from pathlib import Path


def log_event(
    log_path: str,
    phase: str,
    event: str,
    logical_role: str,
    runner: str,
    reason: Optional[str] = None,
) -> None:
    """
    Append a single log line to the logbook.
    
    Format:
    HH:MM:SS Phase X | event | LogicalRole -> runner (reason)
    
    Examples:
    13:04:11 Phase 13 | launch  | Implementer -> implementer (o-dev tier)
    13:18:42 Phase 13 | done    | Implementer exit=0 next=Tester
    13:18:42 Phase 13 | stop    | §8 senior debugger limit reached
    """
    timestamp = time.strftime("%H:%M:%S")
    
    if runner:
        event_text = f"{logical_role} -> {runner}"
    else:
        event_text = logical_role
    
    if reason:
        line = f"{timestamp} {phase} | {event:8} | {event_text} ({reason})\n"
    else:
        line = f"{timestamp} {phase} | {event:8} | {event_text}\n"
    
    # Ensure directory exists
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)