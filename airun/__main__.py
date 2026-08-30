"""Command-line interface for the ai-run orchestrator."""

import argparse
import os
import sys
from typing import Optional

from airun.state import read_project_state
from airun.config import load_config
from airun.runtime import RuntimeState
from airun.routing import resolve, Decision
from airun.errors import InvalidStateError, StopRequired
from airun.logbook import log_event
from airun.guards import check_ignore_guard


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="AI workflow orchestrator",
        prog="python -m airun",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # ai-next command
    next_parser = subparsers.add_parser(
        "next",
        help="Resolve next role and optionally execute it",
    )
    next_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print decision without executing",
    )
    
    return parser.parse_args()


def _print_dry_run_info(
    state_path: str,
    project_state,
    config,
    runtime_state,
    decision: Decision,
) -> None:
    """Print detailed information for dry-run mode."""
    print(f"Project: {project_state.name}")
    print(f"Active Phase: {project_state.active_phase}")
    print(f"Status: {project_state.status}")
    print(f"Logical Next Role: {decision.logical_role}")
    
    if decision.action == "launch":
        print(f"Resolved Runner: {decision.runner}")
        runner_config = config["roles"].get(decision.runner)
        if runner_config:
            command = runner_config["command"].copy()
            command.append(config["kickoff_prompt"])
            print(f"Command: {' '.join(command)}")
    else:
        print(f"Resolved Runner: {decision.runner}")
    
    print(f"Current Phase Counters:")
    for role, count in runtime_state["counters"].items():
        if count > 0:
            print(f"  {role}: {count}")
    print(f"Total Runs: {runtime_state['total_runs']}")
    
    print(f"Limits:")
    print(f"  phase_max_executions: {config['limits']['phase_max_executions']}")
    print(f"  senior_debugger_max: {config['limits']['senior_debugger_max']}")
    print(f"  designer_max: {config['limits']['designer_max']}")
    
    if decision.action == "stop":
        print(f"Stop Reason: {decision.reason}")
        print(f"Rule: {decision.rule}")
    
    # Print deliverable pointers if available
    raw = project_state.raw
    if "Plan" in raw:
        print(f"Plan: {raw['Plan']}")
    if "UI Specification" in raw:
        print(f"UI Specification: {raw['UI Specification']}")
    if "QA Report" in raw:
        print(f"QA Report: {raw['QA Report']}")
    if "Debug Report" in raw:
        print(f"Debug Report: {raw['Debug Report']}")
    if "Review Report" in raw:
        print(f"Review Report: {raw['Review Report']}")


def next_command(args: argparse.Namespace) -> int:
    """Execute the 'next' subcommand."""
    # Determine paths
    cwd = os.getcwd()
    state_path = os.path.join(cwd, "project-state.md")
    runtime_path = os.path.join(cwd, ".ai-run-state.json")
    log_path = os.path.join(cwd, ".ai-run.log")
    
    try:
        # Load project state
        project_state = read_project_state(state_path)
        
        # Load configuration
        config = load_config()
        
        # Load runtime state
        runtime = RuntimeState(runtime_path)
        runtime_data = runtime.load(project_state.active_phase)
        counters = runtime.get_counters()
        total_runs = runtime.get_total_runs()
        
        # Prepare counters dict for routing (including total_runs as expected by tests)
        routing_counters = counters.copy()
        routing_counters["total_runs"] = total_runs
        
        # Prepare runtime state dict for display
        runtime_state = {
            "counters": counters,
            "total_runs": total_runs,
            "phase": runtime.get_phase()
        }
        
        # Apply routing logic
        decision = resolve(project_state, routing_counters, config["limits"])
        
        # Check ignore guard (only for dry-run - Phase 5 acceptance criterion 8)
        if args.dry_run:
            ignore_result = check_ignore_guard(cwd)
            if ignore_result:
                print(f"Ignore guard violation: {ignore_result}")
                return 4
        
        # For dry-run, just print information
        if args.dry_run:
            _print_dry_run_info(
                state_path, project_state, config, runtime_state, decision
            )
            
            # Exit codes per specification
            if decision.action == "launch":
                return 0
            elif decision.action == "stop":
                return 2
            else:
                return 4  # Should not happen
        
        # Real execution (for Phase 7, not Phase 5)
        print("Real execution not implemented in Phase 5", file=sys.stderr)
        return 1
        
    except InvalidStateError as e:
        print(f"Invalid state: {e}", file=sys.stderr)
        return 4
    except StopRequired as e:
        print(f"Stop required: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def main() -> None:
    """Main entry point."""
    args = parse_args()
    
    if args.command == "next":
        exit_code = next_command(args)
        sys.exit(exit_code)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()