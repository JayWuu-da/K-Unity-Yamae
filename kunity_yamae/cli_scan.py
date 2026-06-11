import json

import click
from rich.console import Console
from rich.panel import Panel

from .scanner import UnityProjectScanner

console = Console()


@click.command("scan")
@click.option("--deep", is_flag=True, help="Deep scan including assembly graph")
@click.option("--write-memory", is_flag=True, help="Write UNITY_AGENTS.md memory files")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def scan_cmd(ctx, deep: bool, write_memory: bool, as_json: bool) -> None:
    config = ctx.obj["config"]
    project_path = ctx.obj["project_path"]
    scanner = UnityProjectScanner(project_path, config)
    profile = scanner.scan(deep=deep)

    output_path = project_path / ".unity-harness" / "project-profile.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(profile, file, indent=2)

    if write_memory:
        scanner.write_memory_files(profile)

    if as_json:
        click.echo(
            json.dumps(
                {
                    "schema": "unity-harness.scan-result.v1",
                    "deep": deep,
                    "memory_written": write_memory,
                    "profile_path": str(output_path),
                    "profile": profile,
                },
                indent=2,
            )
        )
        return

    if write_memory:
        console.print("[green]Memory files written.[/green]")

    console.print(
        Panel.fit(
            f"[bold]Unity Project Profile[/bold]\n"
            f"Version: {profile.get('unity_version', 'unknown')}\n"
            f"Packages: {len(profile.get('packages', {}))}\n"
            f"Assemblies: {len(profile.get('assemblies', []))}\n"
            f"Scenes: {len(profile.get('scenes', []))}\n"
            f"Protected patterns: {len(profile.get('protected_patterns', []))}",
            title="Project Scan",
        )
    )
    console.print(f"[dim]Profile saved to {output_path}[/dim]")
