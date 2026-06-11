import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from tests.fixtures.make_unity_project import create_minimal_project


def test_guard_diff_json_detects_serialized_rename_without_migration(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    script = tmp_path / "Assets" / "PlayerStats.cs"
    script.write_text(
        "\n".join(
            [
                "using UnityEngine;",
                "public sealed class PlayerStats : MonoBehaviour",
                "{",
                "    [SerializeField] private int hitpoints;",
                "}",
            ]
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "baseline"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    script.write_text(
        "\n".join(
            [
                "using UnityEngine;",
                "public sealed class PlayerStats : MonoBehaviour",
                "{",
                "    [SerializeField] private int health;",
                "}",
            ]
        ),
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "guard-diff", "--json"])

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["issues"][0]["guard"] == "serialized_rename"
    assert payload["issues"][0]["severity"] == "hard_failure"
    assert len(payload["issues"]) == 1
    assert payload["status"] == "failed"
