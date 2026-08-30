"""Error types for the ai-run orchestrator."""

class InvalidStateError(Exception):
    """Raised when project-state.md cannot be parsed or is invalid."""
    pass

class StopRequired(Exception):
    """Raised when the orchestrator must stop without launching."""
    def __init__(self, reason: str, rule: str = ""):
        super().__init__(reason)
        self.reason = reason
        self.rule = rule