import click
from rich.console import Console

from .ledger import EvidenceLedger
from .modes import select_mode
from .risk import RiskClassifier
from .scanner import UnityProjectScanner

console = Console()


@click.command("work")
@click.argument("task")
@click.option("--auto", is_flag=True, help="Auto-select mode from risk")
@click.option(
    "--mode",
    type=click.Choice(
        [
            "fast_patch",
            "standard",
            "asset_safe",
            "migration",
            "validation_only",
        ]
    ),
    default=None,
)
@click.option("--agent", default=None, help="Agent backend (codex/claude/gemini/kimi/glm/mimo)")
@click.pass_context
def work_cmd(ctx, task: str, auto: bool, mode: str | None, agent: str | None) -> None:
    config = ctx.obj["config"]
    project_path = ctx.obj["project_path"]
    profile = UnityProjectScanner(project_path, config).scan()
    risk_report = RiskClassifier(config).classify(task, profile)
    selected_mode = mode or select_mode(risk_report["risk_score"], config)
    ledger = EvidenceLedger(project_path)
    ledger.start_task(task, selected_mode, risk_report)

    console.print(f"[bold]Mode: {selected_mode}[/bold] (risk: {risk_report['risk_score']})")
    console.print(f"[dim]Agent: {agent or config['agents']['default']}[/dim]")

    agent_name = agent or config["agents"]["default"]
    try:
        from .agents import get_agent

        agent_backend = get_agent(agent_name, config)
        result = agent_backend.execute(task, project_path, risk_report, selected_mode, ledger)
        if result.get("status") == "error":
            ledger.add_event("agent_error", {"error": result.get("message", "unknown")})
            console.print(f"[red]Agent error: {result.get('message', 'unknown')}[/red]")
        else:
            console.print(f"[green]Task completed: {result.get('status', 'unknown')}[/green]")
    except Exception as exc:
        console.print(f"[red]Agent execution failed: {exc}[/red]")
        ledger.add_event("agent_error", {"error": str(exc)})

    report_path = ledger.finalize()
    console.print(f"[dim]Ledger saved to {report_path}[/dim]")
