"""Configuration loader for K-Unity-Yamae."""

import os
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "default.yml"


def load_config(project_path: Path, custom_config: str | None = None) -> dict[str, Any]:
    """Load configuration from default, project, and optional custom paths."""
    config = _load_yaml(DEFAULT_CONFIG_PATH)

    project_config = project_path / ".unity-harness" / "config.yml"
    if project_config.exists():
        overrides = _load_yaml(project_config)
        config = _deep_merge(config, overrides)

    if custom_config:
        custom = _load_yaml(Path(custom_config))
        config = _deep_merge(config, custom)

    config = _resolve_env_vars(config)
    return config


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _resolve_env_vars(obj: Any) -> Any:
    if isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        env_var = obj[2:-1]
        return os.environ.get(env_var, "")
    if isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env_vars(v) for v in obj]
    return obj


def find_unity_project(start: Path | None = None) -> Path | None:
    """Walk up from start to find a Unity project root (has ProjectSettings/)."""
    current = (start or Path.cwd()).resolve()
    for _ in range(20):
        if (current / "ProjectSettings").is_dir():
            return current
        if current.parent == current:
            break
        current = current.parent
    return None
