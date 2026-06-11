import json
from pathlib import Path
from typing import Final

from .unity_profile import load_cached_profile

UNITY_MCP_PACKAGE_URL: Final[
    str
] = "https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main"

QA_LEVEL_DEFAULTS: Final[dict[str, dict[str, bool]]] = {
    "minimal": {
        "compile": True,
        "editmode": True,
        "playmode": False,
        "release_build": False,
    },
    "standard": {
        "compile": True,
        "editmode": True,
        "playmode": True,
        "release_build": False,
    },
    "release": {
        "compile": True,
        "editmode": True,
        "playmode": True,
        "release_build": True,
    },
}


def qa_level_defaults(qa_level: str, has_explicit_selection: bool) -> dict[str, bool]:
    if has_explicit_selection:
        return {
            "compile": False,
            "editmode": False,
            "playmode": False,
            "release_build": False,
        }
    defaults = QA_LEVEL_DEFAULTS.get(qa_level)
    if defaults is None:
        raise ValueError(f"unsupported qa_level: {qa_level}")
    return defaults


def unity_mcp_plan(enabled: bool, visual_smoke: bool) -> dict:
    return {
        "recommended": True,
        "enabled": enabled,
        "package_url": UNITY_MCP_PACKAGE_URL,
        "reason": (
            "Use Unity MCP when the claim depends on live Editor state, Game View, "
            "console, tests, or screenshots."
        ),
        "scenario": _unity_mcp_scenario(visual_smoke),
    }


def visual_smoke_plan(enabled: bool) -> dict:
    return {
        "enabled": enabled,
        "screenshot_name": "visual-smoke.png",
        "pass_observable": (
            "Game View screenshot exists, is non-empty, and expected runtime VFX "
            "objects are present in hierarchy evidence."
        ),
    }


def test_assembly_suggestions(project_path: Path) -> list[str]:
    profile = load_cached_profile(project_path)
    tests = profile.get("tests", {})
    raw_paths = tests.get("test_asmdefs", [])
    suggestions: list[str] = []
    if not isinstance(raw_paths, list):
        return suggestions
    for raw_path in raw_paths:
        if not isinstance(raw_path, str):
            continue
        asmdef_path = project_path / raw_path
        if not asmdef_path.exists():
            continue
        try:
            data = json.loads(asmdef_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        name = data.get("name")
        if isinstance(name, str) and name not in suggestions:
            suggestions.append(name)
    return suggestions


def _unity_mcp_scenario(visual_smoke: bool) -> list[str]:
    scenario = [
        "refresh_unity(mode='if_dirty', scope='all', compile='request', wait_for_ready=True)",
        "run_tests(mode='EditMode', assembly_names='<suggested-test-assembly>')",
        "manage_editor.play",
    ]
    if visual_smoke:
        scenario.append(
            "manage_camera.screenshot(capture_source='game_view', "
            "screenshot_file_name='visual-smoke.png')"
        )
        scenario.append(
            "manage_scene.get_hierarchy(page_size='120', max_depth='1', "
            "include_transform='false')"
        )
    scenario.extend(
        [
            "read_console(types=['error'])",
            "manage_editor.stop",
        ]
    )
    return scenario
