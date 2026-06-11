from pathlib import Path

from kunity_yamae.config import load_config
from kunity_yamae.scanner import UnityProjectScanner
from tests.fixtures.make_unity_project import create_ui_graphics_architecture_project


def test_editor_probe_report_includes_ui_component_state() -> None:
    source = Path("Editor/EditorInspectionProbe.cs").read_text(encoding="utf-8")
    serializer = Path("Editor/EditorInspectionJson.cs").read_text(encoding="utf-8")

    assert "UiComponentStateFact" in source
    assert "Interactable" in source
    assert "RaycastTarget" in source
    assert "BlocksRaycasts" in source
    assert "uiComponentStates" in serializer


def test_graphics_facts_include_audio_model_sprite_importers(tmp_path: Path) -> None:
    create_ui_graphics_architecture_project(tmp_path, include_importer_variety=True)
    config = load_config(tmp_path)

    profile = UnityProjectScanner(tmp_path, config).scan(deep=True)
    graphics = profile["graphics_defaults"]

    assert graphics["sprite_import_settings"][0]["path"] == "Assets/Textures/Hero.png.meta"
    assert graphics["sprite_import_settings"][0]["sprite_mode"] == "Single"
    assert graphics["audio_import_settings"][0]["path"] == "Assets/Audio/Click.wav.meta"
    assert graphics["audio_import_settings"][0]["load_type"] == "CompressedInMemory"
    assert graphics["model_import_settings"][0]["path"] == "Assets/Models/Hero.fbx.meta"
    assert graphics["model_import_settings"][0]["mesh_compression"] == "Medium"
