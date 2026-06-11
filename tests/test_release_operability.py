import json
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from tests.fixtures.make_unity_project import create_minimal_project


def test_release_check_command_reports_package_data_and_quality_gates(
    tmp_path: Path,
) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "release-check", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.release-check.v1"
    assert payload["status"] == "passed"
    assert payload["package_data"]["config_default"] is True
    assert payload["package_data"]["rule_cards"] >= 9
    assert payload["package_data"]["editor_sources"] >= 3
    assert "python -m pytest -q" in payload["quality_gates"]
    assert "python -m ruff check ." in payload["quality_gates"]


def test_docs_do_not_contain_stale_mvp_bug_claims() -> None:
    stale_phrases = [
        "MVP has **14 bugs**",
        "Rule card files | 7 (unused by code)",
        "Test files | 3",
        "All 7 rule card .md files | Entire content | Never loaded by code",
    ]
    docs = [
        Path("docs/ANALYSIS.md"),
        Path("docs/UPGRADE_REPORT.md"),
    ]

    combined = "\n".join(path.read_text(encoding="utf-8") for path in docs)

    for phrase in stale_phrases:
        assert phrase not in combined
