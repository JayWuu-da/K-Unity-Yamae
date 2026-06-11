import json
import re
from json import JSONDecodeError
from pathlib import Path

from .constants import GENERATED_FOLDERS
from .unity_profile import collect_unity_facts


def build_inspection_report(project_path: Path, packages: dict[str, str]) -> dict:
    unity_facts = collect_unity_facts(project_path, packages)
    hierarchy = _inspect_hierarchy(project_path)
    prefabs = _inspect_prefabs(project_path)
    editor_probe = _load_editor_probe(project_path)
    return {
        "schema": "unity-harness.inspect-report.v1",
        "hierarchy": hierarchy,
        "prefabs": prefabs,
        "ui": unity_facts["ui_system"],
        "graphics": unity_facts["graphics_defaults"],
        "platform_targets": unity_facts["platform_targets"],
        "render_pipeline": unity_facts["render_pipeline"],
        "input_system": unity_facts["input_system"],
        "editor_probe": editor_probe,
    }


def _inspect_hierarchy(project_path: Path) -> dict:
    scene_paths = list(_iter_files(project_path, "*.unity"))
    prefab_instance_count = 0
    event_system_count = 0
    scene_names: list[str] = []
    for path in scene_paths:
        content = path.read_text(encoding="utf-8", errors="replace")
        prefab_instance_count += content.count("PrefabInstance:")
        event_system_count += content.count("EventSystem")
        scene_names.append(_relative(project_path, path))
    return {
        "scene_count": len(scene_paths),
        "scenes": scene_names[:25],
        "prefab_instance_count": prefab_instance_count,
        "event_system_count": event_system_count,
    }


def _inspect_prefabs(project_path: Path) -> dict:
    prefab_paths = list(_iter_files(project_path, "*.prefab"))
    missing_scripts: list[str] = []
    nested_prefab_count = 0
    for path in prefab_paths:
        content = path.read_text(encoding="utf-8", errors="replace")
        nested_prefab_count += content.count("PrefabInstance:")
        if re.search(r"m_Script:\s*\{[^}]*guid:\s*0{32}", content):
            missing_scripts.append(_relative(project_path, path))
    return {
        "prefab_count": len(prefab_paths),
        "prefabs": [_relative(project_path, path) for path in prefab_paths[:25]],
        "nested_prefab_count": nested_prefab_count,
        "missing_script_count": len(missing_scripts),
        "missing_script_prefabs": missing_scripts[:25],
    }


def _iter_files(project_path: Path, pattern: str) -> list[Path]:
    paths: list[Path] = []
    for path in project_path.rglob(pattern):
        try:
            relative_parts = path.relative_to(project_path).parts
        except ValueError:
            continue
        if GENERATED_FOLDERS & set(relative_parts):
            continue
        paths.append(path)
    return paths


def _relative(project_path: Path, path: Path) -> str:
    return str(path.relative_to(project_path)).replace("\\", "/")


def _load_editor_probe(project_path: Path) -> dict:
    report_path = project_path / ".unity-harness" / "reports" / "editor-inspection.json"
    if not report_path.exists():
        return {
            "status": "unavailable",
            "path": _relative(project_path, report_path),
            "message": (
                "Run Unity batchmode executeMethod "
                "KUnityYamae.Editor.HarnessChecks.RunEditorInspection."
            ),
        }

    try:
        payload = json.loads(report_path.read_text(encoding="utf-8-sig"))
    except JSONDecodeError as exc:
        return {
            "status": "invalid",
            "path": _relative(project_path, report_path),
            "message": f"Invalid editor inspection JSON: {exc.msg}",
        }
    if not isinstance(payload, dict):
        return {
            "status": "invalid",
            "path": _relative(project_path, report_path),
            "message": "Editor inspection JSON root must be an object.",
        }

    return {
        "status": "available",
        "path": _relative(project_path, report_path),
        "schema": payload.get("schema", "unknown"),
        "generated_by": payload.get("generatedBy", "unknown"),
        "inspector_connections": _normalize_probe_section(
            payload.get("inspectorConnections", {})
        ),
        "prefab_overrides": _normalize_probe_section(payload.get("prefabOverrides", {})),
        "serialized_references": _normalize_probe_section(
            payload.get("serializedReferences", {})
        ),
        "ui_component_states": _normalize_probe_section(payload.get("uiComponentStates", {})),
    }


def _normalize_probe_section(value):
    if isinstance(value, dict):
        return {
            _snake_case(str(key)): _normalize_probe_section(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_normalize_probe_section(item) for item in value]
    return value


def _snake_case(value: str) -> str:
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return value.replace("-", "_").lower()
