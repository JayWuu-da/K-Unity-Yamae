import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--git-init", action="store_true")
    args = parser.parse_args()

    target = Path(args.out)
    match args.kind:
        case "minimal":
            create_minimal_project(target)
        case "ui-graphics-architecture":
            create_ui_graphics_architecture_project(target)
        case "ui-no-eventsystem":
            create_ui_graphics_architecture_project(target, include_event_system=False)
        case "graphics-mismatch":
            create_ui_graphics_architecture_project(target, graphics_mismatch=True)
        case "graphics-platforms":
            create_ui_graphics_architecture_project(target)
        case "ambiguous-architecture":
            create_ui_graphics_architecture_project(target, ambiguous_architecture=True)
        case "serialized-rename-diff":
            create_ui_graphics_architecture_project(target)
        case unknown:
            print(f"unknown fixture kind: {unknown}", file=sys.stderr)
            return 2

    if args.git_init:
        import subprocess

        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "fixture@example.com"],
            cwd=target,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Fixture"],
            cwd=target,
            check=True,
            capture_output=True,
        )
        subprocess.run(["git", "add", "."], cwd=target, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "test fixture"],
            cwd=target,
            check=True,
            capture_output=True,
        )

    print(f"FIXTURE_OK {target}")
    return 0


def create_minimal_project(project_path: Path) -> None:
    (project_path / "ProjectSettings").mkdir(parents=True, exist_ok=True)
    (project_path / "ProjectSettings" / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 6000.4.0f1\n",
        encoding="utf-8",
    )
    (project_path / "Packages").mkdir(parents=True, exist_ok=True)
    (project_path / "Packages" / "manifest.json").write_text(
        json.dumps({"dependencies": {}}),
        encoding="utf-8",
    )
    (project_path / "Assets").mkdir(parents=True, exist_ok=True)


def create_ui_graphics_architecture_project(
    project_path: Path,
    *,
    include_event_system: bool = True,
    graphics_mismatch: bool = False,
    ambiguous_architecture: bool = False,
    include_importer_variety: bool = False,
) -> None:
    create_minimal_project(project_path)
    (project_path / "ProjectSettings" / "ProjectSettings.asset").write_text(
        "activeInputHandler: 2\n",
        encoding="utf-8",
    )
    (project_path / "Packages" / "manifest.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "com.unity.ugui": "2.0.0",
                    "com.unity.inputsystem": "1.8.2",
                }
            }
        ),
        encoding="utf-8",
    )
    _write_ui_assets(project_path, include_event_system)
    _write_graphics_assets(project_path, graphics_mismatch, include_importer_variety)
    _write_architecture_scripts(project_path, ambiguous_architecture)


def _write_ui_assets(project_path: Path, include_event_system: bool) -> None:
    (project_path / "Assets" / "Scenes").mkdir(parents=True, exist_ok=True)
    (project_path / "Assets" / "UI").mkdir(parents=True, exist_ok=True)
    scene_tokens = [
        "GameObject:",
        "  m_Name: MainCanvas",
        "Canvas:",
        "GraphicRaycaster:",
        "PrefabInstance:",
        "  m_SourcePrefab: {fileID: 100100000, guid: mainmenu, type: 3}",
    ]
    if include_event_system:
        scene_tokens.append("EventSystem:")
    (project_path / "Assets" / "Scenes" / "Main.unity").write_text(
        "\n".join(scene_tokens) + "\n",
        encoding="utf-8",
    )
    (project_path / "Assets" / "UI" / "MainMenu.prefab").write_text(
        "\n".join(
            [
                "GameObject:",
                "  m_Name: MainMenu",
                "Canvas:",
                "GraphicRaycaster:",
                "CanvasGroup:",
                "m_RaycastTarget: 1",
                "m_OnClick:",
                "MonoBehaviour:",
                "  m_Script: {fileID: 11500000, guid: 00000000000000000000000000000000, type: 3}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_graphics_assets(
    project_path: Path,
    graphics_mismatch: bool,
    include_importer_variety: bool,
) -> None:
    (project_path / "Assets" / "Textures").mkdir(parents=True, exist_ok=True)
    standalone_format = "RGBA32" if graphics_mismatch else "ASTC_6x6"
    (project_path / "Assets" / "Textures" / "Hero.png").write_bytes(b"png")
    (project_path / "Assets" / "Textures" / "Hero.png.meta").write_text(
        "\n".join(
            [
                "TextureImporter:",
                "  spriteMode: 1",
                "  spritePixelsToUnits: 100",
                "  mipmapEnabled: 1",
                "  isReadable: 0",
                "  maxTextureSize: 4096",
                "  platformSettings:",
                "  - buildTarget: Android",
                "    maxTextureSize: 2048",
                "    textureCompression: Compressed",
                "    format: ASTC_6x6",
                "    compressionQuality: 50",
                "    crunchedCompression: 1",
                "  - buildTarget: iPhone",
                "    maxTextureSize: 2048",
                "    textureCompression: Compressed",
                "    format: ASTC_6x6",
                "    compressionQuality: 50",
                "    crunchedCompression: 1",
                "  - buildTarget: Standalone",
                "    maxTextureSize: 4096",
                "    textureCompression: Uncompressed",
                f"    format: {standalone_format}",
                "    compressionQuality: 100",
                "    crunchedCompression: 0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    if not include_importer_variety:
        return
    (project_path / "Assets" / "Audio").mkdir(parents=True, exist_ok=True)
    (project_path / "Assets" / "Models").mkdir(parents=True, exist_ok=True)
    (project_path / "Assets" / "Audio" / "Click.wav").write_bytes(b"wav")
    (project_path / "Assets" / "Audio" / "Click.wav.meta").write_text(
        "\n".join(
            [
                "AudioImporter:",
                "  loadType: CompressedInMemory",
                "  compressionFormat: Vorbis",
                "  quality: 0.7",
                "  preloadAudioData: 1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project_path / "Assets" / "Models" / "Hero.fbx").write_bytes(b"fbx")
    (project_path / "Assets" / "Models" / "Hero.fbx.meta").write_text(
        "\n".join(
            [
                "ModelImporter:",
                "  meshCompression: Medium",
                "  isReadable: 0",
                "  optimizeMeshPolygons: 1",
                "  importBlendShapes: 0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_architecture_scripts(project_path: Path, ambiguous_architecture: bool) -> None:
    (project_path / "Assets" / "Scripts").mkdir(parents=True, exist_ok=True)
    presenter_name = "ShopPresenter" if not ambiguous_architecture else "ShopThing"
    (project_path / "Assets" / "Scripts" / f"{presenter_name}.cs").write_text(
        "\n".join(
            [
                "using UnityEngine;",
                f"public sealed class {presenter_name} : MonoBehaviour",
                "{",
                "    [SerializeField] private GameObject view;",
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project_path / "Assets" / "Scripts" / "GameController.cs").write_text(
        "using UnityEngine;\npublic sealed class GameController : MonoBehaviour {}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
