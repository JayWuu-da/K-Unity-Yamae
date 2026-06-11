import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from tests.fixtures.make_unity_project import create_minimal_project


def test_guarded_agent_patch_reports_error_message_and_cleanup_receipt(tmp_path: Path) -> None:
    _create_git_fixture(tmp_path)
    config_path = _write_config(tmp_path, "not a patch")
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "--config",
            str(config_path),
            "run",
            "Malformed patch",
            "--agent",
            "local-patch",
            "--guarded-agent-patch",
            "--json",
        ],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["agent_patch"]["status"] == "invalid_patch"
    assert payload["agent_patch"]["error"]
    assert payload["agent_patch"]["cleanup"]["worktree_removed"] is True


def test_guarded_agent_patch_does_not_leave_new_file_or_index_state_when_blocked(
    tmp_path: Path,
) -> None:
    _create_git_fixture(tmp_path)
    config_path = _write_config(tmp_path, _new_prefab_patch())
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "--config",
            str(config_path),
            "run",
            "Add generated prefab",
            "--agent",
            "local-patch",
            "--guarded-agent-patch",
            "--apply-agent-patch",
            "--json",
        ],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["agent_patch"]["applied"] is False
    assert payload["agent_patch"]["cleanup"]["rolled_back"] is True
    assert not (tmp_path / "Assets" / "NewUI.prefab").exists()
    status = subprocess.run(
        ["git", "status", "--porcelain", "-u"],
        cwd=tmp_path,
        check=True,
        text=True,
        capture_output=True,
    )
    assert "Assets/NewUI.prefab" not in status.stdout


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


def _write_config(project_path: Path, patch: str) -> Path:
    config_path = project_path / ".unity-harness" / "config.yml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "\n".join(
            [
                "agents:",
                "  default: local-patch",
                "  backends:",
                "    local-patch:",
                "      enabled: true",
                "      patch: |",
                *[f"        {line}" for line in patch.splitlines()],
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def _new_prefab_patch() -> str:
    return "\n".join(
        [
            "diff --git a/Assets/NewUI.prefab b/Assets/NewUI.prefab",
            "new file mode 100644",
            "index 0000000..9c942f5",
            "--- /dev/null",
            "+++ b/Assets/NewUI.prefab",
            "@@ -0,0 +1,2 @@",
            "+GameObject:",
            "+  m_Name: NewUI",
            "",
        ]
    )
