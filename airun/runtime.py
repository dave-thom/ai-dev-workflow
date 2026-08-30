"""Runtime state management (.ai-run-state.json)."""

import json
import os
import tempfile
from typing import Dict, Any, Optional
from .errors import StopRequired


class RuntimeState:
    """Manages the .ai-run-state.json file."""
    
    SCHEMA_VERSION = 1
    
    def __init__(self, path: str = ".ai-run-state.json"):
        self.path = path
        self._data: Optional[Dict[str, Any]] = None
    
    def load(self, current_phase: str) -> Dict[str, Any]:
        """
        Load runtime state, reconciling with current phase.
        
        Args:
            current_phase: Current Active Phase from project-state.md
        
        Returns:
            Counter dictionary for the current phase.
        
        Raises:
            StopRequired: If state file is invalid or corrupted.
        """
        # Initialize default structure
        default_data = {
            "schema": self.SCHEMA_VERSION,
            "phase": current_phase,
            "counters": {
                "implementer": 0,
                "senior_implementer": 0,
                "designer": 0,
                "tester": 0,
                "debugger": 0,
                "senior_debugger": 0,
                "reviewer": 0,
                "git": 0
            },
            "total_runs": 0
        }
        
        # If file doesn't exist, return default
        if not os.path.exists(self.path):
            self._data = default_data
            return self._data["counters"]
        
        # Load and parse JSON
        try:
            with open(self.path, 'r') as f:
                self._data = json.load(f)
        except json.JSONDecodeError:
            raise StopRequired(
                f"Runtime state file {self.path} contains invalid JSON",
                "runtime corruption"
            )
        
        # Validate schema
        if not isinstance(self._data, dict):
            raise StopRequired(
                f"Runtime state file {self.path} root must be an object",
                "runtime corruption"
            )
        
        if self._data.get("schema") != self.SCHEMA_VERSION:
            raise StopRequired(
                f"Runtime state file {self.path} has unsupported schema version {self._data.get('schema')}",
                "runtime corruption"
            )
        
        # Validate counters structure
        if "counters" not in self._data:
            raise StopRequired(
                f"Runtime state file {self.path} missing counters key",
                "runtime corruption"
            )
        
        counters = self._data["counters"]
        if not isinstance(counters, dict):
            raise StopRequired(
                f"Runtime state file {self.path} counters must be an object",
                "runtime corruption"
            )
        
        # Validate each counter
        required_counters = default_data["counters"].keys()
        for counter_name in required_counters:
            if counter_name not in counters:
                counters[counter_name] = 0
            
            value = counters[counter_name]
            if not isinstance(value, int) or value < 0:
                raise StopRequired(
                    f"Runtime state file {self.path} counter {counter_name} must be non-negative integer, got {value}",
                    "runtime corruption"
                )
        
        # Ensure total_runs exists and is valid
        if "total_runs" not in self._data:
            self._data["total_runs"] = 0
        
        total_runs = self._data["total_runs"]
        if not isinstance(total_runs, int) or total_runs < 0:
            raise StopRequired(
                f"Runtime state file {self.path} total_runs must be non-negative integer, got {total_runs}",
                "runtime corruption"
            )
        
        # Check if total_runs is at least the sum of counters
        counter_sum = sum(counters.values())
        if total_runs < counter_sum:
            raise StopRequired(
                f"Runtime state file {self.path} total_runs ({total_runs}) less than sum of counters ({counter_sum})",
                "runtime corruption"
            )
        
        # Phase reconciliation
        stored_phase = self._data.get("phase")
        if stored_phase != current_phase:
            # Reset all counters and phase
            self._data["phase"] = current_phase
            self._data["counters"] = default_data["counters"].copy()
            self._data["total_runs"] = 0
        
        return self._data["counters"]
    
    def increment_counter(self, runner: str) -> None:
        """
        Increment a runner's counter and total_runs.
        
        Args:
            runner: Runner name (e.g., "implementer", "debugger")
        
        Raises:
            ValueError: If runner is not a known counter.
            RuntimeError: If load() hasn't been called first.
        """
        if self._data is None:
            raise RuntimeError("Must call load() before increment_counter()")
        
        if runner not in self._data["counters"]:
            raise ValueError(f"Unknown runner: {runner}")
        
        self._data["counters"][runner] += 1
        self._data["total_runs"] += 1
    
    def save(self) -> None:
        """
        Save runtime state atomically (temp file + rename).
        
        Raises:
            RuntimeError: If load() hasn't been called first.
            OSError: If file operations fail.
        """
        if self._data is None:
            raise RuntimeError("Must call load() before save()")
        
        # Create temporary file in same directory
        dirname = os.path.dirname(self.path) or "."
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=dirname,
            prefix=os.path.basename(self.path) + ".",
            delete=False
        ) as tmp:
            json.dump(self._data, tmp, indent=2)
            tmp.flush()
            tmp_name = tmp.name
        
        try:
            # Atomic rename
            os.replace(tmp_name, self.path)
        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
    
    def get_counters(self) -> Dict[str, int]:
        """Get current counter values."""
        if self._data is None:
            raise RuntimeError("Must call load() before get_counters()")
        return self._data["counters"].copy()
    
    def get_total_runs(self) -> int:
        """Get total_runs value."""
        if self._data is None:
            raise RuntimeError("Must call load() before get_total_runs()")
        return self._data["total_runs"]
    
    def get_phase(self) -> str:
        """Get stored phase."""
        if self._data is None:
            raise RuntimeError("Must call load() before get_phase()")
        return self._data["phase"]