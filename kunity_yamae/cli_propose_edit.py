import json
import subprocess
from pathlib import Path

import click

from .guarded_edits import GuardedEditError, GuardedEditWorkflow


@click.command("propose-edit")
@click.argument("task", required=False)
@click.option(
    "--patch-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Unified diff file to validate.",
)
@click.option("--apply", "apply_patch", is_flag=True, help="Apply after guards pass.")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def propose_edit_cmd(
    ctx,
    task: str | None,
    patch_file: Path,
    apply_patch: bool,
    as_json: bool,
) -> None:
    project_path: Path = ctx.obj["project_path"]
    config = ctx.obj["config"]
    patch_text = patch_file.read_text(encoding="utf-8")
    workflow = GuardedEditWorkflow(project_path, config)
    try:
        result = workflow.apply(patch_text) if apply_patch else workflow.evaluate(patch_text)
    except (GuardedEditError, subprocess.CalledProcessError) as exc:
        result = {"status": "error", "applied": False, "issues": [], "error": str(exc)}

    payload = {
        "schema": "unity-harness.proposed-edit.v1",
        "task": task,
        "patch_file": str(patch_file),
        "apply_requested": apply_patch,
        **result,
    }
    if as_json:
        click.echo(json.dumps(payload, indent=2))
    else:
        click.echo(f"{payload['status']}: {patch_file}")

    if payload["status"] not in {"ready_to_apply", "applied"}:
        ctx.exit(2)
