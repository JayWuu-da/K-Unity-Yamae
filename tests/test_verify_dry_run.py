import json
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from tests.fixtures.make_unity_project import create_minimal_project


def test_verify_dry_run_outputs_unity_batchmode_commands(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "verify", "--compile-only", "--dry-run", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.verify-result.v1"
    assert payload["dry_run"] is True
    command = payload["results"][0]["command"]
    assert "-batchmode" in command
    assert "-quit" in command
    assert "-projectPath" in command
    assert str(tmp_path) in command
