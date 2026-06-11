import json

import click

from .editor_probe_stage import stage_editor_probe
from .inspector import build_inspection_report
from .scanner import UnityProjectScanner
from .verifier import UnityVerifier


@click.command("inspect")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.option(
    "--editor-probe",
    is_flag=True,
    help="Run Unity Editor batchmode inspection before reading the report.",
)
@click.pass_context
def inspect_cmd(ctx, as_json: bool, editor_probe: bool) -> None:
    config = ctx.obj["config"]
    project_path = ctx.obj["project_path"]
    scanner = UnityProjectScanner(project_path, config)
    profile = scanner.scan(deep=True)
    probe_results = []
    if editor_probe:
        with stage_editor_probe(project_path):
            probe_results = UnityVerifier(project_path, config).verify(
                compile_check=False,
                custom_method="KUnityYamae.Editor.HarnessChecks.RunEditorInspection",
            )
    report = build_inspection_report(project_path, profile.get("packages", {}))
    if editor_probe:
        report["editor_probe_run"] = probe_results
    if as_json:
        click.echo(json.dumps(report, indent=2))
        return
    click.echo(f"Scenes: {report['hierarchy']['scene_count']}")
    click.echo(f"Prefabs: {report['prefabs']['prefab_count']}")
    click.echo(f"Missing scripts: {report['prefabs']['missing_script_count']}")
    editor_probe = report["editor_probe"]
    ui_component_states = editor_probe.get("ui_component_states", {})
    click.echo(f"Editor probe: {editor_probe['status']}")
    click.echo(f"UI component states: {ui_component_states.get('component_count', 0)}")
