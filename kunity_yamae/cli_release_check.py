import json
from pathlib import Path

import click

from .agents import list_agents
from .cli_run import run_cmd

QUALITY_GATES = ["python -m pytest -q", "python -m ruff check ."]


@click.command("release-check")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def release_check_cmd(ctx, as_json: bool) -> None:
    package_root = Path(__file__).resolve().parent.parent
    package_data = _collect_package_data(package_root)
    failed = [key for key, value in package_data.items() if not value]
    payload = {
        "schema": "unity-harness.release-check.v1",
        "status": "failed" if failed else "passed",
        "package_root": str(package_root),
        "project_path": str(ctx.obj["project_path"]),
        "package_data": package_data,
        "cli_surface": _collect_cli_surface(),
        "agent_registry": _collect_agent_registry(),
        "quality_gates": QUALITY_GATES,
        "failed_checks": failed,
    }
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        if failed:
            ctx.exit(2)
        return

    click.echo(f"status: {payload['status']}")
    for key, value in package_data.items():
        click.echo(f"{key}: {value}")
    if failed:
        ctx.exit(2)


def _collect_package_data(package_root: Path) -> dict:
    return {
        "config_default": (package_root / "config" / "default.yml").exists(),
        "rule_cards": len(list((package_root / "kunity_yamae" / "rules").glob("*.md"))),
        "editor_sources": len(list((package_root / "Editor").glob("*.cs"))),
        "release_checklist": (package_root / "docs" / "RELEASE_CHECKLIST.md").exists(),
    }


def _collect_cli_surface() -> dict:
    option_names = {
        option
        for parameter in run_cmd.params
        for option in [
            *getattr(parameter, "opts", []),
            *getattr(parameter, "secondary_opts", []),
        ]
    }
    return {
        "run_has_guarded_agent_patch": "--guarded-agent-patch" in option_names,
        "run_has_apply_agent_patch": "--apply-agent-patch" in option_names,
        "run_has_no_verify": "--no-verify" in option_names,
        "run_has_no_guard": "--no-guard" in option_names,
    }


def _collect_agent_registry() -> dict:
    agents = set(list_agents())
    return {
        "local_patch": "local-patch" in agents,
        "count": len(agents),
    }
