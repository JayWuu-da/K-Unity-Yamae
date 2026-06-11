import json
from pathlib import Path

from click.testing import CliRunner

import kunity_yamae.cli_inspect as cli_inspect
from kunity_yamae.cli import main


def create_project(project_path: Path) -> None:
    (project_path / "ProjectSettings").mkdir()
    (project_path / "ProjectSettings" / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 6000.4.0f1\n",
        encoding="utf-8",
    )
    (project_path / "ProjectSettings" / "ProjectSettings.asset").write_text(
        "activeInputHandler: 2\n",
        encoding="utf-8",
    )
    (project_path / "Packages").mkdir()
    (project_path / "Packages" / "manifest.json").write_text(
        json.dumps({"dependencies": {"com.unity.ugui": "2.0.0"}}),
        encoding="utf-8",
    )
    (project_path / "Assets" / "Scenes").mkdir(parents=True)
    (project_path / "Assets" / "UI").mkdir(parents=True)
    (project_path / "Assets" / "Scenes" / "Main.unity").write_text(
        "GameObject:\nPrefabInstance:\n",
        encoding="utf-8",
    )
    (project_path / "Assets" / "UI" / "ShopButton.prefab").write_text(
        "GameObject:\n  m_Name: ShopButton\n",
        encoding="utf-8",
    )


def write_editor_probe_report(project_path: Path, content: dict) -> None:
    report_path = project_path / ".unity-harness" / "reports" / "editor-inspection.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(content), encoding="utf-8")


def make_probe_payload() -> dict:
    return {
        "schema": "unity-harness.editor-inspection.v1",
        "generatedBy": "KUnityYamae.Editor.HarnessChecks.RunEditorInspection",
        "inspectorConnections": {
            "persistentListenerCount": 1,
            "listeners": [
                {
                    "assetPath": "Assets/UI/ShopButton.prefab",
                    "gameObjectPath": "ShopButton",
                    "componentType": "UnityEngine.UI.Button",
                    "methodName": "OpenShop",
                    "targetAssetPath": "Assets/Scripts/ShopPresenter.cs",
                    "targetType": "ShopPresenter",
                }
            ],
        },
        "prefabOverrides": {
            "instanceCount": 1,
            "modifiedPropertyCount": 2,
            "removedComponentCount": 0,
            "addedComponentCount": 1,
            "instances": [],
        },
        "serializedReferences": {
            "missingObjectReferenceCount": 1,
            "missingReferences": [
                {
                    "assetPath": "Assets/UI/ShopButton.prefab",
                    "gameObjectPath": "ShopButton",
                    "componentType": "ShopButtonView",
                    "propertyPath": "presenter",
                }
            ],
        },
        "uiComponentStates": {
            "componentCount": 1,
            "components": [
                {
                    "assetPath": "Assets/UI/ShopButton.prefab",
                    "gameObjectPath": "Canvas/ShopButton",
                    "componentType": "UnityEngine.UI.Button",
                    "interactable": "True",
                    "raycastTarget": "",
                    "blocksRaycasts": "",
                }
            ],
        },
    }


def test_inspect_json_merges_editor_probe_report(tmp_path: Path) -> None:
    create_project(tmp_path)
    write_editor_probe_report(tmp_path, make_probe_payload())
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "inspect", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["editor_probe"]["status"] == "available"
    assert payload["editor_probe"]["schema"] == "unity-harness.editor-inspection.v1"
    assert payload["editor_probe"]["inspector_connections"]["persistent_listener_count"] == 1
    assert (
        payload["editor_probe"]["inspector_connections"]["listeners"][0]["target_asset_path"]
        == "Assets/Scripts/ShopPresenter.cs"
    )
    assert payload["editor_probe"]["prefab_overrides"]["modified_property_count"] == 2
    assert payload["editor_probe"]["serialized_references"]["missing_object_reference_count"] == 1
    assert payload["editor_probe"]["ui_component_states"]["component_count"] == 1
    assert (
        payload["editor_probe"]["ui_component_states"]["components"][0]["game_object_path"]
        == "Canvas/ShopButton"
    )


def test_inspect_json_reports_invalid_editor_probe_without_breaking_static_inspection(
    tmp_path: Path,
) -> None:
    create_project(tmp_path)
    report_path = tmp_path / ".unity-harness" / "reports" / "editor-inspection.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("{not-json", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "inspect", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["editor_probe"]["status"] == "invalid"
    assert payload["editor_probe"]["path"].endswith(".unity-harness/reports/editor-inspection.json")
    assert payload["hierarchy"]["scene_count"] == 1
    assert payload["prefabs"]["prefab_count"] == 1


def test_inspect_editor_probe_option_runs_unity_probe_before_reporting(
    tmp_path: Path,
    monkeypatch,
) -> None:
    create_project(tmp_path)
    calls = []

    class FakeVerifier:
        def __init__(self, project_path: Path, config: dict) -> None:
            self.project_path = project_path
            self.config = config

        def verify(
            self,
            compile_check: bool = True,
            editmode_tests: bool = False,
            playmode_tests: bool = False,
            build_target: str | None = None,
            custom_method: str | None = None,
        ) -> list[dict]:
            calls.append(
                {
                    "compile_check": compile_check,
                    "editmode_tests": editmode_tests,
                    "playmode_tests": playmode_tests,
                    "build_target": build_target,
                    "custom_method": custom_method,
                }
            )
            write_editor_probe_report(self.project_path, make_probe_payload())
            return [{"name": "custom_RunEditorInspection", "status": "passed", "passed": True}]

    monkeypatch.setattr(cli_inspect, "UnityVerifier", FakeVerifier)
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "inspect", "--editor-probe", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert calls == [
        {
            "compile_check": False,
            "editmode_tests": False,
            "playmode_tests": False,
            "build_target": None,
            "custom_method": "KUnityYamae.Editor.HarnessChecks.RunEditorInspection",
        }
    ]
    assert payload["editor_probe"]["status"] == "available"
    assert payload["editor_probe_run"][0]["status"] == "passed"


def test_inspect_editor_probe_option_stages_and_cleans_probe_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    create_project(tmp_path)
    staged_root = tmp_path / "Assets" / "Editor" / "KUnityYamaeHarness"

    class FakeVerifier:
        def __init__(self, project_path: Path, config: dict) -> None:
            self.project_path = project_path
            self.config = config

        def verify(
            self,
            compile_check: bool = True,
            editmode_tests: bool = False,
            playmode_tests: bool = False,
            build_target: str | None = None,
            custom_method: str | None = None,
        ) -> list[dict]:
            assert (staged_root / "HarnessChecks.cs").exists()
            assert (staged_root / "EditorInspectionProbe.cs").exists()
            assert (staged_root / "EditorInspectionJson.cs").exists()
            (tmp_path / "Assets" / "Editor.meta").write_text("folder meta", encoding="utf-8")
            (tmp_path / "Assets" / "Editor" / "KUnityYamaeHarness.meta").write_text(
                "folder meta",
                encoding="utf-8",
            )
            (staged_root / "HarnessChecks.cs.meta").write_text("meta", encoding="utf-8")
            (staged_root / "EditorInspectionProbe.cs.meta").write_text("meta", encoding="utf-8")
            (staged_root / "EditorInspectionJson.cs.meta").write_text("meta", encoding="utf-8")
            write_editor_probe_report(self.project_path, make_probe_payload())
            return [{"name": "custom_RunEditorInspection", "status": "passed", "passed": True}]

    monkeypatch.setattr(cli_inspect, "UnityVerifier", FakeVerifier)
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "inspect", "--editor-probe", "--json"],
    )

    assert result.exit_code == 0, result.output
    assert not staged_root.exists()
    assert not (tmp_path / "Assets" / "Editor.meta").exists()
    assert not (tmp_path / "Assets" / "Editor" / "KUnityYamaeHarness.meta").exists()
    assert json.loads(result.output)["editor_probe"]["status"] == "available"


def test_inspect_editor_probe_reports_unavailable_when_unity_writes_no_report(
    tmp_path: Path,
    monkeypatch,
) -> None:
    create_project(tmp_path)

    class FakeVerifier:
        def __init__(self, project_path: Path, config: dict) -> None:
            self.project_path = project_path
            self.config = config

        def verify(
            self,
            compile_check: bool = True,
            editmode_tests: bool = False,
            playmode_tests: bool = False,
            build_target: str | None = None,
            custom_method: str | None = None,
        ) -> list[dict]:
            return [{"name": "custom_RunEditorInspection", "status": "passed", "passed": True}]

    monkeypatch.setattr(cli_inspect, "UnityVerifier", FakeVerifier)
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "inspect", "--editor-probe", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["editor_probe_run"][0]["status"] == "passed"
    assert payload["editor_probe"]["status"] == "unavailable"
