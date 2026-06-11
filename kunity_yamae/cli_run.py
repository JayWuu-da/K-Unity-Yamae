import json
import subprocess

import click
from rich.console import Console

from .cli_providers import build_provider_doctor
from .context import ContextSelector
from .guarded_edits import GuardedEditError, GuardedEditWorkflow
from .guards import DiffGuard
from .ledger import EvidenceLedger
from .modes import select_mode
from .reporter import ReportWriter
from .risk import RiskClassifier
from .scanner import UnityProjectScanner
from .verifier import UnityVerifier

console = Console()


@click.command("run")
@click.argument("task")
@click.option("--agent", default=None, help="Agent backend")
@click.option("--verify/--no-verify", "do_verify", default=True, help="Run verification after.")
@click.option("--guard/--no-guard", "do_guard", default=True, help="Run guards after.")
@click.option("--plan-only", is_flag=True, help="Emit a non-mutating harness plan.")
@click.option("--context-only", is_flag=True, help="Emit selected context without agent execution.")
@click.option("--provider-check", is_flag=True, help="Run provider doctor before agent execution.")
@click.option("--verify-dry-run", is_flag=True, help="Include planned Unity commands.")
@click.option("--editor-probe", is_flag=True, help="Plan an editor probe verification stage.")
@click.option(
    "--guarded-agent-patch",
    is_flag=True,
    help="Treat agent output as a unified diff and run it through guards.",
)
@click.option("--apply-agent-patch", is_flag=True, help="Apply guarded agent patch if clean.")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def run_cmd(
    ctx,
    task: str,
    agent: str | None,
    do_verify: bool,
    do_guard: bool,
    plan_only: bool,
    context_only: bool,
    provider_check: bool,
    verify_dry_run: bool,
    editor_probe: bool,
    guarded_agent_patch: bool,
    apply_agent_patch: bool,
    as_json: bool,
) -> None:
    config = ctx.obj["config"]
    project_path = ctx.obj["project_path"]
    agent_name = agent or config["agents"]["default"]
    profile = UnityProjectScanner(project_path, config).scan()
    risk_report = RiskClassifier(config).classify(task, profile)
    selected_mode = select_mode(risk_report["risk_score"], config)

    if provider_check:
        provider_payload = build_provider_doctor(config, provider=agent_name)
        provider_status = next(iter(provider_payload["providers"].values()))["status"]
        if provider_status not in {"ready", "disabled"}:
            payload = {
                "schema": "unity-harness.run-result.v1",
                "status": "failed",
                "failed_stage": "provider_check",
                "agent": agent_name,
                "agent_executed": False,
                "provider_requests": 0,
                "provider": provider_payload,
            }
            if as_json:
                click.echo(json.dumps(payload, indent=2))
            else:
                console.print(f"[red]Provider check failed: {provider_status}[/red]")
            ctx.exit(2)

    if plan_only or context_only:
        payload = _build_lightweight_run_payload(
            project_path=project_path,
            config=config,
            task=task,
            risk_report=risk_report,
            selected_mode=selected_mode,
            plan_only=plan_only,
            context_only=context_only,
            verify_dry_run=verify_dry_run,
            editor_probe=editor_probe,
        )
        if as_json:
            click.echo(json.dumps(payload, indent=2))
            return
        console.print(json.dumps(payload, indent=2))
        return

    quiet_json = as_json and (guarded_agent_patch or apply_agent_patch)
    if not quiet_json:
        console.print("[bold cyan]K-Unity-Yamae Pipeline[/bold cyan]")
        console.print(f"[dim]Task: {task}[/dim]\n")
        _print_risk_step(risk_report, selected_mode)
    ledger = EvidenceLedger(project_path)
    ledger.start_task(task, selected_mode, risk_report)
    agent_result = _run_agent_step(
        agent_name,
        config,
        project_path,
        task,
        risk_report,
        selected_mode,
        ledger,
        quiet=quiet_json,
    )
    if guarded_agent_patch or apply_agent_patch:
        payload = _handle_agent_patch(
            project_path=project_path,
            config=config,
            agent_name=agent_name,
            agent_result=agent_result,
            apply_patch=apply_agent_patch,
        )
        if as_json:
            click.echo(json.dumps(payload, indent=2))
        else:
            console.print(json.dumps(payload, indent=2))
        if payload["status"] == "failed":
            ctx.exit(2)
        return

    if do_guard:
        _run_guard_step(project_path, config)
    if do_verify:
        _run_verification_step(project_path, config, risk_report)
    _write_report_step(project_path, task, selected_mode, risk_report, ledger)


def _print_risk_step(risk_report: dict, selected_mode: str) -> None:
    console.print("[bold]Step 1: Risk Classification[/bold]")
    console.print(f"  Score: {risk_report['risk_score']} | Mode: {selected_mode}")
    if risk_report.get("triggers"):
        console.print(f"  Triggers: {', '.join(risk_report['triggers'][:3])}")
    console.print()


def _run_agent_step(
    agent_name: str,
    config: dict,
    project_path,
    task: str,
    risk_report: dict,
    selected_mode: str,
    ledger: EvidenceLedger,
    *,
    quiet: bool = False,
) -> dict:
    if not quiet:
        console.print("[bold]Step 2: Agent Execution[/bold]")
    try:
        from .agents import get_agent

        agent_backend = get_agent(agent_name, config)
        result = agent_backend.execute(task, project_path, risk_report, selected_mode, ledger)
        if result.get("status") == "error":
            if not quiet:
                console.print(f"  [red]Error: {result.get('message', 'unknown')}[/red]")
            ledger.add_event("agent_error", {"error": result.get("message", "unknown")})
            return result
        else:
            if not quiet:
                console.print(f"  [green]Completed via {agent_name}[/green]")
            changes = result.get("changes", [])
            if changes and not quiet:
                console.print(f"  Files to change: {len(changes)}")
            return result
    except Exception as exc:
        if not quiet:
            console.print(f"  [red]Failed: {exc}[/red]")
        ledger.add_event("agent_error", {"error": str(exc)})
        return {"status": "error", "message": str(exc)}


def _handle_agent_patch(
    *,
    project_path,
    config: dict,
    agent_name: str,
    agent_result: dict,
    apply_patch: bool,
) -> dict:
    if agent_result.get("status") == "error":
        return {
            "schema": "unity-harness.run-result.v1",
            "status": "failed",
            "failed_stage": "agent_execution",
            "agent": agent_name,
            "agent_executed": True,
            "provider_requests": 1,
            "agent_patch": None,
            "error": agent_result.get("message", "unknown"),
        }
    patch_text = str(agent_result.get("output", ""))
    workflow = GuardedEditWorkflow(project_path, config)
    try:
        patch_result = workflow.apply(patch_text) if apply_patch else workflow.evaluate(patch_text)
    except (GuardedEditError, subprocess.CalledProcessError) as exc:
        patch_result = {"status": "error", "applied": False, "issues": [], "error": str(exc)}
    except Exception as exc:
        patch_result = {"status": "error", "applied": False, "issues": [], "error": str(exc)}
    clean_statuses = {"ready_to_apply", "applied"}
    status = "completed" if patch_result["status"] in clean_statuses else "failed"
    return {
        "schema": "unity-harness.run-result.v1",
        "status": status,
        "failed_stage": None if status == "completed" else "agent_patch_guard",
        "agent": agent_name,
        "agent_executed": True,
        "provider_requests": 1,
        "agent_patch": patch_result,
    }


def _run_guard_step(project_path, config: dict) -> None:
    console.print("\n[bold]Step 3: Guard Check[/bold]")
    from .guards import DiffGuard

    issues = DiffGuard(project_path, config).check()
    if not issues:
        console.print("  [green]No issues found[/green]")
        return
    hard = [issue for issue in issues if issue["severity"] == "hard_failure"]
    warn = [issue for issue in issues if issue["severity"] == "warning"]
    console.print(
        f"  [red]Hard failures: {len(hard)}[/red] | [yellow]Warnings: {len(warn)}[/yellow]"
    )
    for issue in issues[:5]:
        console.print(f"  - [{issue['severity']}] {issue['guard']}: {issue['message'][:80]}")


def _run_verification_step(project_path, config: dict, risk_report: dict) -> None:
    console.print("\n[bold]Step 4: Verification[/bold]")
    results = UnityVerifier(project_path, config).verify(
        compile_check=True,
        editmode_tests=risk_report["risk_score"] >= 30,
        playmode_tests=risk_report["risk_score"] >= 60,
    )
    for result in results:
        color = "green" if result["passed"] else "red"
        console.print(
            f"  [{color}]Tier {result.get('tier', '?')}: "
            f"{result['name']} - {result['status']}[/{color}]"
        )
        if not result["passed"]:
            console.print(f"    {result.get('details', '')[:100]}")


def _write_report_step(
    project_path,
    task: str,
    selected_mode: str,
    risk_report: dict,
    ledger: EvidenceLedger,
) -> None:
    console.print("\n[bold]Step 5: Report[/bold]")
    report_path = ledger.finalize()
    console.print(f"  Ledger: {report_path}")
    writer = ReportWriter(project_path)
    events = writer.read_last_ledger()
    if events:
        report_md = writer.write_report(events, risk_report, task, selected_mode)
        console.print(f"  Report: {report_md}")
    console.print("\n[bold cyan]Pipeline complete[/bold cyan]")


def _build_lightweight_run_payload(
    *,
    project_path,
    config: dict,
    task: str,
    risk_report: dict,
    selected_mode: str,
    plan_only: bool,
    context_only: bool,
    verify_dry_run: bool,
    editor_probe: bool,
) -> dict:
    context = ContextSelector(project_path, config).select(task, risk_report, selected_mode)
    guard_issues = DiffGuard(project_path, config).check()
    verifier = UnityVerifier(project_path, config)
    verify_commands = []
    if verify_dry_run:
        verify_commands = verifier.plan(
            compile_check=True,
            editmode_tests=risk_report["risk_score"] >= 30,
            playmode_tests=risk_report["risk_score"] >= 60,
            custom_method=(
                "KUnityYamae.Editor.HarnessChecks.RunEditorInspection"
                if editor_probe
                else None
            ),
        )
    ledger = EvidenceLedger(project_path)
    ledger.start_task(task, selected_mode, risk_report)
    ledger.add_event("run_planned", {"plan_only": plan_only, "context_only": context_only})
    return {
        "schema": "unity-harness.run-result.v1",
        "status": "planned",
        "plan_only": plan_only,
        "context_only": context_only,
        "provider_requests": 0,
        "agent_executed": False,
        "risk_report": risk_report,
        "context": context,
        "guard": {
            "status": "failed"
            if any(issue.get("severity") == "hard_failure" for issue in guard_issues)
            else "passed",
            "issues": guard_issues,
        },
        "verify_commands": verify_commands,
        "stages": [
            {"stage": "scan", "status": "ok"},
            {"stage": "risk", "status": "ok"},
            {"stage": "context", "status": "ok"},
            {"stage": "guard", "status": "ok"},
            {"stage": "verify", "status": "planned" if verify_dry_run else "not_requested"},
        ],
        "report_path": str(project_path / ".unity-harness" / "last-ledger.jsonl"),
    }
