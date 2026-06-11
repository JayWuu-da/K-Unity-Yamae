from pathlib import Path

from kunity_yamae.config import load_config
from kunity_yamae.scanner import UnityProjectScanner
from tests.fixtures.make_unity_project import create_ui_graphics_architecture_project


def test_scan_reports_platform_texture_import_settings(tmp_path: Path) -> None:
    create_ui_graphics_architecture_project(tmp_path, graphics_mismatch=True)
    config = load_config(tmp_path)

    profile = UnityProjectScanner(tmp_path, config).scan(deep=True)
    graphics = profile["graphics_defaults"]

    texture = graphics["texture_import_settings"][0]
    assert texture["path"] == "Assets/Textures/Hero.png.meta"
    assert texture["platforms"]["Android"]["format"] == "ASTC_6x6"
    assert texture["platforms"]["iPhone"]["max_texture_size"] == 2048
    assert texture["platforms"]["Standalone"]["format"] == "RGBA32"
    assert graphics["mobile_pc_mismatches"][0]["path"] == "Assets/Textures/Hero.png.meta"
