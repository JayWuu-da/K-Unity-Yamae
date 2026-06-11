import json
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from tests.fixtures.make_unity_project import create_minimal_project


def test_release_check_reports_cli_help_and_local_patch_agent(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "release-check", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["cli_surface"]["run_has_guarded_agent_patch"] is True
    assert payload["cli_surface"]["run_has_no_verify"] is True
    assert payload["agent_registry"]["local_patch"] is True


def test_providers_doctor_lists_local_patch_as_offline_handoff(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "providers", "doctor", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    handoff = payload["offline_handoffs"]["local-patch"]
    assert handoff["status"] == "ready"
    assert handoff["requires_api_key"] is False
    assert "--guarded-agent-patch" in handoff["usage"]
