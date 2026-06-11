import json
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

import kunity_yamae.agents as agents
from kunity_yamae.cli import main
from tests.fixtures.make_unity_project import create_minimal_project


class FakePatchAgent:
    def __init__(self, name: str, config: dict, agent_config: dict) -> None:
        self.name = name
        self.config = config
        self.agent_config = agent_config

    def execute(
        self,
        task: str,
        project_path: Path,
        risk_report: dict,
        mode: str,
        ledger,
    ) -> dict:
        return {"status": "completed", "output": self.agent_config["patch"]}


def test_run_agent_patch_plan_routes_output_through_guarded_edit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _create_git_fixture(tmp_path)
    monkeypatch.setitem(agents.AGENT_REGISTRY, "fakepatch", FakePatchAgent)
    config_path = _write_config(tmp_path, "fakepatch", _safe_patch())
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "--config",
            str(config_path),
            "run",
            "Add readonly bonus helper",
            "--agent",
            "fakepatch",
            "--guarded-agent-patch",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.run-result.v1"
    assert payload["agent_executed"] is True
    assert payload["agent_patch"]["status"] == "ready_to_apply"
    assert payload["agent_patch"]["applied"] is False
    assert "Bonus" not in (tmp_path / "Assets" / "PlayerStats.cs").read_text(
        encoding="utf-8"
    )


def test_run_agent_patch_apply_blocks_serialized_rename(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _create_git_fixture(tmp_path)
    monkeypatch.setitem(agents.AGENT_REGISTRY, "fakepatch", FakePatchAgent)
    config_path = _write_config(tmp_path, "fakepatch", _rename_patch())
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "--config",
            str(config_path),
            "run",
            "Rename serialized stat",
            "--agent",
            "fakepatch",
            "--guarded-agent-patch",
            "--apply-agent-patch",
            "--json",
        ],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "failed"
    assert payload["failed_stage"] == "agent_patch_guard"
    assert payload["agent_patch"]["status"] == "blocked"
    assert payload["agent_patch"]["issues"][0]["guard"] == "serialized_rename"
    assert "hitpoints" in (tmp_path / "Assets" / "PlayerStats.cs").read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize(
    "asset_path",
    ["Assets/NewUI.prefab", "Assets/NewScene.unity", "Assets/NewConfig.asset"],
)
def test_run_agent_patch_apply_blocks_new_unity_asset_without_meta(
    tmp_path: Path,
    monkeypatch,
    asset_path: str,
) -> None:
    _create_git_fixture(tmp_path)
    monkeypatch.setitem(agents.AGENT_REGISTRY, "fakepatch", FakePatchAgent)
    config_path = _write_config(tmp_path, "fakepatch", _new_unity_asset_patch(asset_path))
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
            "fakepatch",
            "--guarded-agent-patch",
            "--apply-agent-patch",
            "--json",
        ],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "failed"
    assert payload["failed_stage"] == "agent_patch_guard"
    assert payload["agent_patch"]["applied"] is False
    guards = {issue["guard"] for issue in payload["agent_patch"]["issues"]}
    assert "meta_pair" in guards
    assert "yaml_write" in guards
    assert not (tmp_path / asset_path).exists()


def test_run_agent_patch_returns_json_failure_for_non_git_project(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    config_path = _write_config(tmp_path, "local-patch", _safe_patch())
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "--config",
            str(config_path),
            "run",
            "Patch non git project",
            "--agent",
            "local-patch",
            "--guarded-agent-patch",
            "--json",
        ],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "failed"
    assert payload["failed_stage"] == "agent_patch_guard"
    assert payload["agent_patch"]["status"] == "error"


def test_run_agent_patch_returns_json_failure_for_empty_patch(tmp_path: Path) -> None:
    _create_git_fixture(tmp_path)
    config_path = _write_config(tmp_path, "local-patch", "")
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "--config",
            str(config_path),
            "run",
            "Empty patch",
            "--agent",
            "local-patch",
            "--guarded-agent-patch",
            "--json",
        ],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "failed"
    assert payload["failed_stage"] == "agent_execution"
    assert payload["error"] == "local-patch requires patch or patch_file"


def test_run_agent_patch_returns_json_failure_for_malformed_patch(tmp_path: Path) -> None:
    _create_git_fixture(tmp_path)
    config_path = _write_config(tmp_path, "local-patch", "not a patch")
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
    assert payload["status"] == "failed"
    assert payload["failed_stage"] == "agent_patch_guard"
    assert payload["agent_patch"]["status"] == "invalid_patch"


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


def _write_config(project_path: Path, agent_name: str, patch: str) -> Path:
    config_path = project_path / ".unity-harness" / "config.yml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    escaped_patch = "\n".join(f"          {line}" for line in patch.splitlines())
    config_path.write_text(
        "\n".join(
            [
                "agents:",
                f"  default: {agent_name}",
                "  backends:",
                f"    {agent_name}:",
                "      enabled: true",
                "      patch: |",
                escaped_patch,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


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


def _new_unity_asset_patch(asset_path: str) -> str:
    filename = Path(asset_path).name
    return "\n".join(
        [
            f"diff --git a/{asset_path} b/{asset_path}",
            "new file mode 100644",
            "index 0000000..9c942f5",
            "--- /dev/null",
            f"+++ b/{asset_path}",
            "@@ -0,0 +1,2 @@",
            "+GameObject:",
            f"+  m_Name: {filename}",
            "",
        ]
    )
