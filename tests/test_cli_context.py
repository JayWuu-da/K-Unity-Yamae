import json
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main


def create_project(project_path: Path) -> None:
    (project_path / "ProjectSettings").mkdir()
    (project_path / "ProjectSettings" / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 6000.4.0f1\n", encoding="utf-8"
    )
    (project_path / "Packages").mkdir()
    (project_path / "Packages" / "manifest.json").write_text(
        json.dumps({"dependencies": {"com.unity.ugui": "2.0.0"}}),
        encoding="utf-8",
    )
    (project_path / "Assets" / "UI").mkdir(parents=True)
    (project_path / "Assets" / "UI" / "ShopButton.prefab").write_text(
        "GameObject:\n  m_Name: ShopButton\nCanvas:\nGraphicRaycaster:\nm_OnClick:\n",
        encoding="utf-8",
    )


def test_context_command_outputs_json_context_pack(tmp_path: Path) -> None:
    create_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "context", "Fix UI button onClick raycast issue"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.context-pack.v1"
    assert "unity.ui" in payload["rule_cards"]
    assert payload["unity_facts"]["ui_system"]["prefab_count"] == 1
