from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main


def create_project(project_path: Path) -> None:
    (project_path / "ProjectSettings").mkdir()
    (project_path / "ProjectSettings" / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 6000.4.0f1\n", encoding="utf-8"
    )


def test_risk_command_remains_available_after_cli_split(tmp_path: Path) -> None:
    create_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "risk", "Fix UI button"])

    assert result.exit_code == 0, result.output
    assert "Risk Report" in result.output
    assert "unity.ui" in result.output
