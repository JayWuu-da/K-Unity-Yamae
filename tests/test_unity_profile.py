import json
from pathlib import Path

from kunity_yamae.scanner import UnityProjectScanner


def make_config() -> dict:
    return {
        "protected_files": {
            "block_direct_write": ["Assets/**/*.meta"],
            "escalate_direct_write": ["Assets/**/*.asmdef"],
            "never_touch": ["Library/**"],
        }
    }


def write_project_files(project_path: Path) -> None:
    (project_path / "ProjectSettings").mkdir()
    (project_path / "ProjectSettings" / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 6000.4.0f1\n", encoding="utf-8"
    )
    (project_path / "ProjectSettings" / "ProjectSettings.asset").write_text(
        "activeInputHandler: 2\n", encoding="utf-8"
    )
    (project_path / "ProjectSettings" / "GraphicsSettings.asset").write_text(
        "m_RenderPipelineAsset: "
        "{fileID: 11400000, guid: 11111111111111111111111111111111, type: 2}\n",
        encoding="utf-8",
    )
    (project_path / "Packages").mkdir()
    (project_path / "Packages" / "manifest.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "com.unity.render-pipelines.universal": "17.0.0",
                    "com.unity.inputsystem": "1.8.2",
                    "com.unity.addressables": "2.3.0",
                }
            }
        ),
        encoding="utf-8",
    )
    (project_path / "Assets" / "UI").mkdir(parents=True)
    (project_path / "Assets" / "UI" / "MainMenu.prefab").write_text(
        "\n".join(
            [
                "%YAML 1.1",
                "--- !u!1 &1000",
                "GameObject:",
                "  m_Name: StartButton",
                "--- !u!114 &2000",
                "MonoBehaviour:",
                "  m_Script: {fileID: 11500000, guid: buttonscript, type: 3}",
                "  m_Interactable: 1",
                "  m_OnClick:",
                "    m_PersistentCalls:",
                "      m_Calls: []",
                "--- !u!223 &3000",
                "Canvas:",
                "--- !u!114 &4000",
                "MonoBehaviour:",
                "  m_Script: {fileID: 11500000, guid: graphicraycaster, type: 3}",
            ]
        ),
        encoding="utf-8",
    )
    (project_path / "Assets" / "Scenes").mkdir()
    (project_path / "Assets" / "Scenes" / "Main.unity").write_text(
        "GameObject:\n  m_Name: EventSystem\n", encoding="utf-8"
    )
    (project_path / "Assets" / "Textures").mkdir()
    (project_path / "Assets" / "Textures" / "Hero.png.meta").write_text(
        "\n".join(
            [
                "TextureImporter:",
                "  maxTextureSize: 4096",
                "  textureCompression: 1",
                "  allowsAlphaSplitting: 0",
                "  platformSettings:",
                "  - serializedVersion: 3",
                "    buildTarget: Android",
                "    format: 50",
                "  - serializedVersion: 3",
                "    buildTarget: iPhone",
                "    format: 45",
            ]
        ),
        encoding="utf-8",
    )


def test_scan_reports_unity_production_facts_when_deep_scan(tmp_path: Path) -> None:
    write_project_files(tmp_path)
    scanner = UnityProjectScanner(tmp_path, make_config())

    profile = scanner.scan(deep=True)

    assert profile["render_pipeline"] == "urp"
    assert profile["input_system"] == "both"
    assert "Android" in profile["platform_targets"]
    assert profile["ui_system"]["prefab_count"] == 1
    assert profile["ui_system"]["button_like_count"] == 1
    assert profile["graphics_defaults"]["texture_meta_count"] == 1
    assert profile["graphics_defaults"]["platform_overrides"]["Android"] == 1
    assert profile["asset_summary"]["prefab_count"] == 1
    assert profile["asset_summary"]["scene_count"] == 1
