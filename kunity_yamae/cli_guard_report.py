import json

import click
from rich.console import Console
from rich.table import Table

from .reporter import ReportWriter

console = Console()


@click.command("guard-diff")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def guard_diff_cmd(ctx, as_json: bool) -> None:
    config = ctx.obj["config"]
    project_path = ctx.obj["project_path"]
    from .guards import DiffGuard

    guard = DiffGuard(project_path, config)
    issues = guard.check()
    hard_failures = [issue for issue in issues if issue.get("severity") == "hard_failure"]

    if as_json:
        click.echo(
            json.dumps(
                {
                    "schema": "unity-harness.guard-diff.v1",
                    "status": "failed" if hard_failures else "passed",
                    "issues": issues,
                },
                indent=2,
            )
        )
        if hard_failures:
            ctx.exit(2)
        return

    if not issues:
        console.print("[green]No Unity-specific hazards found in diff.[/green]")
        return

    table = Table(title="Diff Guard Issues")
    table.add_column("Guard", style="bold")
    table.add_column("Severity")
    table.add_column("File")
    table.add_column("Message")
    for issue in issues:
        sev_color = {"hard_failure": "red", "warning": "yellow", "info": "dim"}.get(
            issue["severity"],
            "white",
        )
        table.add_row(
            issue["guard"],
            f"[{sev_color}]{issue['severity']}[/{sev_color}]",
            issue.get("file", ""),
            issue["message"],
        )
    console.print(table)
    if hard_failures:
        ctx.exit(2)


@click.command("report")
@click.option("--last", is_flag=True, help="Show last task report")
@click.pass_context
def report_cmd(ctx, last: bool) -> None:
    project_path = ctx.obj["project_path"]
    ledger_path = project_path / ".unity-harness" / "last-ledger.jsonl"
    if not ledger_path.exists():
        console.print("[yellow]No ledger found. Run a task first.[/yellow]")
        return

    writer = ReportWriter(project_path)
    report = writer.read_last_ledger()
    if report:
        writer.print_report(report)
    else:
        console.print("[yellow]No completed task in ledger.[/yellow]")
