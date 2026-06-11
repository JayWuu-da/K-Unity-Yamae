from pathlib import Path

import click


@click.command("install")
@click.option("--codex", is_flag=True, help="Install a repo-local Codex skill.")
@click.option("--claude", is_flag=True, help="Install a repo-local Claude Code command.")
@click.pass_context
def install_cmd(ctx, codex: bool, claude: bool) -> None:
    project_path: Path = ctx.obj["project_path"]
    install_codex = codex or not claude
    install_claude = claude or not codex
    written: list[str] = []

    if install_codex:
        target = project_path / ".codex" / "skills" / "k-unity-yamae" / "SKILL.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_codex_skill(), encoding="utf-8")
        written.append(str(target))

    if install_claude:
        target = project_path / ".claude" / "commands" / "kunity-yamae.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_claude_command(), encoding="utf-8")
        written.append(str(target))

    for path in written:
        click.echo(f"written: {path}")


def _codex_skill() -> str:
    return "\n".join(
        [
            "---",
            "name: k-unity-yamae",
            "description: Unity production harness context and guard workflow.",
            "---",
            "",
            "# K-Unity-Yamae",
            "",
            "Before editing Unity code, run:",
            "",
            "```bash",
            'kunity-yamae context --pretty "$TASK"',
            "```",
            "",
            "For a full guarded run:",
            "",
            "```bash",
            'kunity-yamae run "$TASK" --agent codex',
            "```",
            "",
            "Use `kunity-yamae inspect --json` for hierarchy, prefab, UI, and graphics facts.",
        ]
    )


def _claude_command() -> str:
    return "\n".join(
        [
            "# kunity-yamae",
            "",
            "Use this command before Unity production edits:",
            "",
            "```bash",
            'kunity-yamae context --pretty "$ARGUMENTS"',
            "```",
            "",
            "Then execute through the guarded harness when mutation is requested:",
            "",
            "```bash",
            'kunity-yamae run "$ARGUMENTS" --agent claude',
            "```",
            "",
            "Check providers with `kunity-yamae providers doctor --json`.",
        ]
    )
