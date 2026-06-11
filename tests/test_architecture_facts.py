from pathlib import Path

from kunity_yamae.config import load_config
from kunity_yamae.scanner import UnityProjectScanner
from tests.fixtures.make_unity_project import create_ui_graphics_architecture_project


def test_scan_detects_mvp_controller_and_game_manager_patterns(tmp_path: Path) -> None:
    create_ui_graphics_architecture_project(tmp_path)
    config = load_config(tmp_path)

    profile = UnityProjectScanner(tmp_path, config).scan(deep=True)
    architecture = profile["architecture_patterns"]

    assert "mvp" in architecture["detected"]
    assert "Assets/Scripts/ShopPresenter.cs" in architecture["presenters"]
    assert "Assets/Scripts/GameController.cs" in architecture["controllers"]
    assert architecture["confidence"] == "high"


def test_scan_reports_low_confidence_for_ambiguous_architecture(tmp_path: Path) -> None:
    create_ui_graphics_architecture_project(tmp_path, ambiguous_architecture=True)
    config = load_config(tmp_path)

    profile = UnityProjectScanner(tmp_path, config).scan(deep=True)
    architecture = profile["architecture_patterns"]

    assert architecture["confidence"] in {"low", "medium"}
    assert "Do not assume architecture ownership from names alone." in architecture["warnings"]
