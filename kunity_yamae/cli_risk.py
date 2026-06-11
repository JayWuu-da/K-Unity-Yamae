import json
import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .risk import RiskClassifier
from .scanner import UnityProjectScanner

console = Console()


def get_git_diff(project_path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(project_path),
            timeout=30,
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


@click.command("risk")
@click.argument("task")
@click.option("--diff", is_flag=True, help="Classify risk based on current git diff")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def risk_cmd(ctx, task, diff, as_json):
    config = ctx.obj["config"]
    project_path = ctx.obj["project_path"]
    scanner = UnityProjectScanner(project_path, config)
    profile = scanner.scan()
    diff_content = get_git_diff(project_path) if diff else ""
    report = RiskClassifier(config).classify(task, profile, diff=diff_content)
    output_path = project_path / ".unity-harness" / "last-risk-report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
    if as_json:
        click.echo(
            json.dumps(
                {
                    "schema": "unity-harness.risk-result.v1",
                    "diff_checked": diff,
                    "report_path": str(output_path),
                    "report": report,
                },
                indent=2,
            )
        )
        return

    table = Table(title="Risk Report")
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Task", report["task"])
    table.add_row("Risk Score", str(report["risk_score"]))
    table.add_row("Mode", report["mode"])
    table.add_row("Triggers", "\n".join(report.get("triggers", [])))
    table.add_row("Required Rules", "\n".join(report.get("required_rule_cards", [])))
    table.add_row("Blocked Operations", "\n".join(report.get("blocked_operations", [])))
    table.add_row("Required Verification", "\n".join(report.get("required_verification", [])))
    console.print(table)
    console.print(f"[dim]Report saved to {output_path}[/dim]")
