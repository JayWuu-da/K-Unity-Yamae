import json

import click

from .context import ContextSelector
from .risk import RiskClassifier
from .scanner import UnityProjectScanner


@click.command("context")
@click.argument("task")
@click.option("--mode", default=None, help="Override selected mode")
@click.option("--deep", is_flag=True, help="Refresh deep Unity profile first")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON")
@click.pass_context
def context_cmd(ctx, task, mode, deep, pretty):
    config = ctx.obj["config"]
    project_path = ctx.obj["project_path"]
    scanner = UnityProjectScanner(project_path, config)
    profile = scanner.scan(deep=deep)
    classifier = RiskClassifier(config)
    risk_report = classifier.classify(task, profile)
    selected_mode = mode or risk_report["mode"]
    context = ContextSelector(project_path, config).select(task, risk_report, selected_mode)
    context["schema"] = "unity-harness.context-pack.v1"
    indent = 2 if pretty else None
    click.echo(json.dumps(context, ensure_ascii=False, indent=indent))
