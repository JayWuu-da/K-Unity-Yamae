import json
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from tests.fixtures.make_unity_project import create_minimal_project


def test_inspect_summary_counts_editor_probe_ui_state(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    _write_probe_report(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "inspect"])

    assert result.exit_code == 0, result.output
    assert "Editor probe: available" in result.output
    assert "UI component states: 2" in result.output


def test_inspect_summary_marks_editor_probe_unavailable_without_report(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "inspect"])

    assert result.exit_code == 0, result.output
    assert "Editor probe: unavailable" in result.output
    assert "UI component states: 0" in result.output


def _write_probe_report(project_path: Path) -> None:
    report_path = project_path / ".unity-harness" / "reports" / "editor-inspection.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "schema": "unity-harness.editor-inspection.v1",
                "generatedBy": "KUnityYamae.Editor.HarnessChecks.RunEditorInspection",
                "uiComponentStates": {
                    "componentCount": 2,
                    "components": [
                        {"gameObjectPath": "Canvas/Button"},
                        {"gameObjectPath": "Canvas/Panel"},
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
