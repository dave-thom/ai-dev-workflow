"""Configuration loading and validation."""

import json
import os
from typing import Dict, Any, List
from .errors import InvalidStateError


def load_config(base_dir: str = None) -> Dict[str, Any]:
    """
    Load configuration from $AI_PLATFORM/config/ai-run.json and merge with
    project-local .ai-run.json if present.
    
    Args:
        base_dir: Base directory for AI Platform. If None, uses parent directory
                  of this module's parent directory.
    
    Returns:
        Configuration dictionary with 'roles' and 'limits' keys.
    
    Raises:
        InvalidStateError: If config files are missing, malformed, or invalid.
    """
    if base_dir is None:
        # Find AI_PLATFORM root by going up from this file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(script_dir)
    
    global_config_path = os.path.join(base_dir, "config", "ai-run.json")
    
    # Load global config
    try:
        with open(global_config_path, 'r') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise InvalidStateError(f"Cannot load global config {global_config_path}: {e}")
    
    # Load and merge project-local config if it exists
    local_config_path = ".ai-run.json"
    if os.path.exists(local_config_path):
        try:
            with open(local_config_path, 'r') as f:
                local_config = json.load(f)
        except json.JSONDecodeError as e:
            raise InvalidStateError(f"Cannot load local config {local_config_path}: {e}")
        
        # Merge kickoff_prompt if present
        if "kickoff_prompt" in local_config:
            config["kickoff_prompt"] = local_config["kickoff_prompt"]
        
        # Merge roles (shallow per key)
        if "roles" in local_config:
            for role_name, role_config in local_config["roles"].items():
                config.setdefault("roles", {})[role_name] = role_config
        
        # Merge limits (shallow per key)
        if "limits" in local_config:
            for limit_name, limit_value in local_config["limits"].items():
                config.setdefault("limits", {})[limit_name] = limit_value
    
    # Validate required structure
    if not isinstance(config.get("kickoff_prompt"), str):
        raise InvalidStateError("kickoff_prompt must be a string")
    
    if "roles" not in config:
        raise InvalidStateError("roles section missing from config")
    
    if "limits" not in config:
        raise InvalidStateError("limits section missing from config")
    
    # Validate roles
    for role_name, role_config in config["roles"].items():
        if not isinstance(role_config, dict):
            raise InvalidStateError(f"Role {role_name} must be an object")
        
        if "command" not in role_config:
            raise InvalidStateError(f"Role {role_name} missing command")
        
        if not isinstance(role_config["command"], list):
            raise InvalidStateError(f"Role {role_name} command must be a list")
        
        if len(role_config["command"]) == 0:
            raise InvalidStateError(f"Role {role_name} command list cannot be empty")
        
        # Ensure all command elements are strings
        for i, cmd_part in enumerate(role_config["command"]):
            if not isinstance(cmd_part, str):
                raise InvalidStateError(
                    f"Role {role_name} command part {i} must be a string, got {type(cmd_part)}"
                )
        
        # Default kickoff to true if not specified
        if "kickoff" not in role_config:
            role_config["kickoff"] = True
        elif not isinstance(role_config["kickoff"], bool):
            raise InvalidStateError(f"Role {role_name} kickoff must be a boolean")
    
    # Validate limits
    required_limits = ["senior_debugger_max", "designer_max", "phase_max_executions"]
    for limit_name in required_limits:
        if limit_name not in config["limits"]:
            raise InvalidStateError(f"Required limit {limit_name} missing")
        
        limit_value = config["limits"][limit_name]
        if not isinstance(limit_value, int) or limit_value < 0:
            raise InvalidStateError(f"Limit {limit_name} must be a non-negative integer")
    
    return config