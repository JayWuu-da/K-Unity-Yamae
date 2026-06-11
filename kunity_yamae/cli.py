from pathlib import Path

import click

from .cli_context import context_cmd
from .cli_guard_report import guard_diff_cmd, report_cmd
from .cli_init_agent import init_agent_cmd
from .cli_inspect import inspect_cmd
from .cli_install import install_cmd
from .cli_propose_edit import propose_edit_cmd
from .cli_providers import providers_cmd
from .cli_release_check import release_check_cmd
from .cli_risk import risk_cmd
from .cli_run import run_cmd
from .cli_scan import scan_cmd
from .cli_verify import verify_cmd
from .cli_work import work_cmd
from .config import load_config


@click.group()
@click.option("--project", "-p", default=".", help="Unity project path")
@click.option("--config", "-c", default=None, help="Config file path")
@click.pass_context
def main(ctx, project: str, config: str | None) -> None:
    ctx.ensure_object(dict)
    ctx.obj["project_path"] = Path(project).resolve()
    ctx.obj["config"] = load_config(ctx.obj["project_path"], config)


main.add_command(context_cmd)
main.add_command(guard_diff_cmd)
main.add_command(inspect_cmd)
main.add_command(install_cmd)
main.add_command(init_agent_cmd)
main.add_command(propose_edit_cmd)
main.add_command(providers_cmd)
main.add_command(report_cmd)
main.add_command(release_check_cmd)
main.add_command(risk_cmd)
main.add_command(run_cmd)
main.add_command(scan_cmd)
main.add_command(verify_cmd)
main.add_command(work_cmd)


if __name__ == "__main__":
    main()
