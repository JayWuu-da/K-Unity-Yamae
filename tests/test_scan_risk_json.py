import json
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from tests.fixtures.make_unity_project import create_ui_graphics_architecture_project


def test_scan_json_emits_profile_schema(tmp_path: Path) -> None:
    create_ui_graphics_architecture_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "scan", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.scan-result.v1"
    assert payload["profile"]["ui_system"]["prefab_count"] == 1
    assert payload["profile"]["ui_system"]["event_system_count"] == 1
    assert payload["profile_path"].endswith("project-profile.json")


def test_risk_json_emits_rule_cards_for_unity_ui_task(tmp_path: Path) -> None:
    create_ui_graphics_architecture_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "risk", "Fix prefab button raycast", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.risk-result.v1"
    assert "unity.ui" in payload["report"]["required_rule_cards"]
    assert payload["report_path"].endswith("last-risk-report.json")
