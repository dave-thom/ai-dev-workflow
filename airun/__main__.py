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
from airun.guards import check_ignore_guard, check_git_handoff_guard
from airun.launcher import launch_runner, check_progress, check_phase_advance_guardrail


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
    
    # ai-run-phase command
    run_phase_parser = subparsers.add_parser(
        "run-phase",
        help="Repeat 'next' until the active phase changes",
    )
    
    # ai-run command
    run_parser = subparsers.add_parser(
        "run",
        help="Repeat 'next' unconditionally across phases",
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
        
        # Check ignore guard (always)
        ignore_result = check_ignore_guard(cwd)
        if ignore_result:
            print(f"Ignore guard violation: {ignore_result}")
            return 4
        
        # Check git handoff guard for Tester role (always when launching)
        if decision.action == "launch" and decision.logical_role.lower() == "tester":
            handoff_result = check_git_handoff_guard(cwd, project_state.branch)
            if handoff_result:
                # This should stop with exit code 2 (role-contract violation)
                print(f"Git handoff guard violation: {handoff_result}")
                return 2
        
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
        
        # Real execution
        if decision.action == "stop":
            # Log stop event
            log_event(
                log_path,
                f"Phase {project_state.active_phase}",
                "stop",
                decision.logical_role,
                decision.runner,
                f"{decision.reason} ({decision.rule})",
            )
            print(f"Stop: {decision.reason} ({decision.rule})", file=sys.stderr)
            return 2
        
        # Launch runner
        runner_config = config["roles"][decision.runner]
        
        # Log launch event
        log_event(
            log_path,
            f"Phase {project_state.active_phase}",
            "launch",
            decision.logical_role,
            decision.runner,
            None,
        )
        
        # Increment counter before launching (so interrupted runs count)
        runtime.increment_counter(decision.runner)
        runtime.save()
        
        # Launch the runner
        print(f"Launching {decision.logical_role} -> {decision.runner}...", file=sys.stderr)
        process = launch_runner(
            runner_config["command"],
            config["kickoff_prompt"],
            runner_config.get("kickoff", True),
            cwd,
        )
        
        if process.returncode != 0:
            print(f"Runtime failure: {decision.logical_role} ({decision.runner}) "
                  f"exited {process.returncode}", file=sys.stderr)
            return 3
        
        # Reload project state to check progress
        new_project_state = read_project_state(state_path)
        
        # Log completion with NEXT ROLE from NEW state (after execution)
        log_event(
            log_path,
            f"Phase {project_state.active_phase}",
            "done",
            decision.logical_role,
            decision.runner,
            f"exit={process.returncode} next={new_project_state.next_role}",
        )
        
        # Check phase-advance guardrail
        guardrail_error = check_phase_advance_guardrail(
            project_state,
            new_project_state,
            decision.logical_role,
        )
        if guardrail_error:
            print(f"Phase-advance guardrail: {guardrail_error}", file=sys.stderr)
            return 2
        
        # Check progress
        progress_made, no_progress_reason = check_progress(
            project_state,
            new_project_state,
            decision.logical_role,
        )
        
        if not progress_made:
            print(
                f"No progress: {no_progress_reason}",
                file=sys.stderr,
            )
            return 2
        
        # Success
        return 0
        
    except InvalidStateError as e:
        print(f"Invalid state: {e}", file=sys.stderr)
        return 4
    except StopRequired as e:
        print(f"Stop required: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def run_phase_command(args: argparse.Namespace) -> int:
    """Execute the 'run-phase' subcommand."""
    cwd = os.getcwd()
    state_path = os.path.join(cwd, "project-state.md")
    
    try:
        # Read initial active phase
        project_state = read_project_state(state_path)
        initial_phase = project_state.active_phase
        
        print(f"Starting phase loop for: {initial_phase}", file=sys.stderr)
        
        loop_count = 0
        while True:
            # Create argparse namespace for 'next' command
            class NextArgs:
                dry_run = False
            
            next_args = NextArgs()
            
            # Execute 'next' command
            exit_code = next_command(next_args)
            
            # If next_command returned non-zero, propagate it
            if exit_code != 0:
                return exit_code
            
            # Reload project state to check phase change
            project_state = read_project_state(state_path)
            current_phase = project_state.active_phase
            
            # Check if phase has changed
            if current_phase != initial_phase:
                print(f"Phase changed: {initial_phase} -> {current_phase}", file=sys.stderr)
                return 0
            
            # Check if workflow has completed (Next Role is Architect or None/empty)
            next_role_lower = project_state.next_role.lower().strip()
            if not next_role_lower:
                print(f"Workflow completed in phase: {current_phase}", file=sys.stderr)
                return 0
            
            # Safety limit to prevent infinite loops
            loop_count += 1
            if loop_count > 1000:  # Extreme safety limit
                print("Safety limit reached: loop_count > 1000", file=sys.stderr)
                return 2
    
    except InvalidStateError as e:
        print(f"Invalid state: {e}", file=sys.stderr)
        return 4
    except StopRequired as e:
        print(f"Stop required: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def run_command(args: argparse.Namespace) -> int:
    """Execute the 'run' subcommand."""
    cwd = os.getcwd()
    state_path = os.path.join(cwd, "project-state.md")
    
    try:
        print("Starting unconditional run loop across phases", file=sys.stderr)
        
        loop_count = 0
        while loop_count < 1000:  # Extreme safety limit
            # Create argparse namespace for 'next' command
            class NextArgs:
                dry_run = False
            
            next_args = NextArgs()
            
            # Execute 'next' command
            exit_code = next_command(next_args)
            
            # If next_command returned non-zero, propagate it
            if exit_code != 0:
                return exit_code
            
            # Reload project state to check for idle completion
            project_state = read_project_state(state_path)
            next_role_lower = project_state.next_role.lower().strip()
            if next_role_lower in ("", "none"):
                print(f"Workflow completed", file=sys.stderr)
                return 0
            
            loop_count += 1
        
        print("Safety limit reached: loop_count >= 1000", file=sys.stderr)
        return 2
    
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
    elif args.command == "run-phase":
        exit_code = run_phase_command(args)
        sys.exit(exit_code)
    elif args.command == "run":
        exit_code = run_command(args)
        sys.exit(exit_code)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()