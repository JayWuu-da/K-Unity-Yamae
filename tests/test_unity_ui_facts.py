from pathlib import Path

from kunity_yamae.config import load_config
from kunity_yamae.scanner import UnityProjectScanner
from tests.fixtures.make_unity_project import create_ui_graphics_architecture_project


def test_scan_reports_prefab_wiring_and_hierarchy_warnings(tmp_path: Path) -> None:
    create_ui_graphics_architecture_project(tmp_path, include_event_system=False)
    config = load_config(tmp_path)

    profile = UnityProjectScanner(tmp_path, config).scan(deep=True)
    ui = profile["ui_system"]

    assert ui["prefab_wiring"][0]["path"] == "Assets/UI/MainMenu.prefab"
    assert ui["prefab_wiring"][0]["button_like_count"] == 1
    assert ui["missing_script_count"] == 1
    assert "missing_event_system" in ui["hierarchy_warnings"]
    assert ui["canvas_group_count"] == 1
