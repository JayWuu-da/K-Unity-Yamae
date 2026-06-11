import json
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from tests.fixtures.make_unity_project import create_minimal_project


def test_init_agent_dry_run_lists_codex_and_claude_files(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "init-agent", "--target", "both", "--dry-run", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.agent-init.v1"
    assert payload["dry_run"] is True
    paths = {item["path"] for item in payload["files"]}
    assert "AGENTS.md" in paths
    assert "CLAUDE.md" in paths
    assert ".claude/commands/kunity-yamae.md" in paths
    assert ".codex/skills/k-unity-yamae/SKILL.md" in paths


def test_init_agent_write_refuses_to_overwrite_existing_agents_md(tmp_path: Path) -> None:
    create_minimal_project(tmp_path)
    existing = tmp_path / "AGENTS.md"
    existing.write_text("existing", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "init-agent", "--target", "codex", "--write", "--json"],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "conflict"
    assert existing.read_text(encoding="utf-8") == "existing"
