import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from tests.fixtures.make_unity_project import create_minimal_project


def test_propose_edit_blocks_serialized_rename_before_apply(tmp_path: Path) -> None:
    _create_git_fixture(tmp_path)
    patch_file = tmp_path / "rename.diff"
    patch_file.write_text(_rename_patch(), encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "propose-edit",
            "rename stat field",
            "--patch-file",
            str(patch_file),
            "--json",
        ],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.proposed-edit.v1"
    assert payload["status"] == "blocked"
    assert payload["applied"] is False
    assert payload["issues"][0]["guard"] == "serialized_rename"
    assert "hitpoints" in (tmp_path / "Assets" / "PlayerStats.cs").read_text(
        encoding="utf-8"
    )


def test_propose_edit_applies_safe_patch_after_guard(tmp_path: Path) -> None:
    _create_git_fixture(tmp_path)
    patch_file = tmp_path / "safe.diff"
    patch_file.write_text(_safe_patch(), encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "propose-edit",
            "--patch-file",
            str(patch_file),
            "--apply",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "applied"
    assert payload["applied"] is True
    assert "Bonus" in (tmp_path / "Assets" / "PlayerStats.cs").read_text(
        encoding="utf-8"
    )


def _create_git_fixture(project_path: Path) -> None:
    create_minimal_project(project_path)
    script = project_path / "Assets" / "PlayerStats.cs"
    script.write_text(
        "\n".join(
            [
                "using UnityEngine;",
                "public sealed class PlayerStats : MonoBehaviour",
                "{",
                "    [SerializeField] private int hitpoints;",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "init"], cwd=project_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=project_path,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project_path, check=True)
    subprocess.run(["git", "add", "."], cwd=project_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "baseline"],
        cwd=project_path,
        check=True,
        capture_output=True,
    )


def _rename_patch() -> str:
    return "\n".join(
        [
            "diff --git a/Assets/PlayerStats.cs b/Assets/PlayerStats.cs",
            "--- a/Assets/PlayerStats.cs",
            "+++ b/Assets/PlayerStats.cs",
            "@@ -1,5 +1,5 @@",
            " using UnityEngine;",
            " public sealed class PlayerStats : MonoBehaviour",
            " {",
            "-    [SerializeField] private int hitpoints;",
            "+    [SerializeField] private int health;",
            " }",
            "",
        ]
    )


def _safe_patch() -> str:
    return "\n".join(
        [
            "diff --git a/Assets/PlayerStats.cs b/Assets/PlayerStats.cs",
            "--- a/Assets/PlayerStats.cs",
            "+++ b/Assets/PlayerStats.cs",
            "@@ -1,5 +1,6 @@",
            " using UnityEngine;",
            " public sealed class PlayerStats : MonoBehaviour",
            " {",
            "     [SerializeField] private int hitpoints;",
            "+    public int Bonus => hitpoints;",
            " }",
            "",
        ]
    )
