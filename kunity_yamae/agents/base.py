"""Base agent interface - all agent adapters implement this."""

import re
from abc import ABC, abstractmethod
from pathlib import Path

from ..ledger import EvidenceLedger

UNITY_SYSTEM_PROMPT = "\n".join(
    [
        "You are editing a Unity project through K-Unity-Yamae, a Unity-specific harness.",
        "",
        "Core rules:",
        "1. Classify Unity risk before editing.",
        "2. Keep changes minimal and explain why each file changed.",
        "3. Do not edit generated folders: Library, Temp, Obj, Logs, Builds, UserSettings.",
        "4. Do not directly write .unity, .prefab, .asset, .controller, .anim, "
        "or .meta files unless the selected mode explicitly permits it.",
        "5. Preserve .meta files and GUID continuity.",
        "6. Treat serialized field/class/asset renames as migrations.",
        "7. Keep UnityEditor code out of runtime assemblies.",
        "8. Report actual verification performed; never claim Editor or Play Mode "
        "validation unless it ran.",
        "",
        "Unity-specific guidance:",
        "- When renaming serialized fields, always add "
        '[FormerlySerializedAs("oldName")] to preserve Inspector data.',
        "- Assets and .meta files must always be paired. Moving/renaming/deleting "
        "an asset requires matching .meta operation.",
        "- Scenes (.unity), prefabs (.prefab), and ScriptableObjects (.asset) contain "
        "serialized object graphs. Direct YAML editing can corrupt them.",
        "- Assembly definitions (.asmdef) control compile boundaries. Editor-only "
        "assemblies must not be referenced by runtime assemblies.",
        "- Resources.Load and Addressables use string keys. Changing paths/keys "
        "without updating all callers breaks runtime.",
    ]
)


class BaseAgent(ABC):
    def __init__(self, name: str, config: dict, agent_config: dict):
        self.name = name
        self.config = config
        self.agent_config = agent_config

    @abstractmethod
    def execute(
        self,
        task: str,
        project_path: Path,
        risk_report: dict,
        mode: str,
        ledger: EvidenceLedger,
    ) -> dict:
        """Execute a task through this agent backend."""
        pass

    def _build_prompt(
        self,
        task: str,
        risk_report: dict,
        mode: str,
        project_path: Path,
        rule_cards: list[str] | None = None,
    ) -> str:
        """Build the full prompt for the agent."""
        from ..context import ContextSelector

        selector = ContextSelector(project_path, self.config)
        ctx = selector.select(task, risk_report, mode)

        prompt_parts = [
            UNITY_SYSTEM_PROMPT,
            f"\n## Task\n{task}",
            f"\n## Risk\nScore: {risk_report.get('risk_score', 0)}, Mode: {mode}",
            "\n## Triggers\n" + "\n".join(f"- {t}" for t in risk_report.get("triggers", [])),
            "\n## Required Rule Cards\n"
            + "\n".join(f"- {r}" for r in rule_cards or risk_report.get("required_rule_cards", [])),
            "\n## Blocked Operations\n"
            + "\n".join(f"- {b}" for b in risk_report.get("blocked_operations", [])),
        ]

        if ctx.get("relevant_files"):
            prompt_parts.append("\n## Relevant Files")
            for f in ctx["relevant_files"]:
                prompt_parts.append(f"- {f}")

        if ctx.get("summaries"):
            prompt_parts.append("\n## File Previews")
            for s in ctx["summaries"]:
                prompt_parts.append(f"\n### {s['path']} ({s['lines']} lines)\n{s['preview']}")

        if ctx.get("project_memory"):
            prompt_parts.append(f"\n## Project Memory\n{ctx['project_memory'][:2000]}")

        if ctx.get("unity_facts"):
            prompt_parts.append(f"\n## Unity Facts\n{ctx['unity_facts']}")

        if ctx.get("manual_checks"):
            prompt_parts.append(
                "\n## Manual Checks\n" + "\n".join(f"- {check}" for check in ctx["manual_checks"])
            )

        rule_content = self._load_rule_cards(
            rule_cards or risk_report.get("required_rule_cards", []),
            project_path,
        )
        if rule_content:
            prompt_parts.append(f"\n## Rule Cards\n{rule_content}")

        prompt_parts.append(
            "\nProvide your changes. For each file, explain the Unity-specific risk decision."
        )
        return "\n".join(prompt_parts)

    def _load_rule_cards(self, rule_names: list[str], project_path: Path) -> str:
        """Load rule card markdown content."""
        rule_map = {
            "unity.global": "global_rules.md",
            "unity.serialized-field-rename": "serialized_field_rename.md",
            "unity.meta-guid": "meta_guid.md",
            "unity.prefab-scene-yaml": "prefab_scene_yaml.md",
            "unity.asmdef": "asmdef.md",
            "unity.editor-runtime-boundary": "editor_runtime_boundary.md",
            "unity.resources-addressables": "resources_addressables.md",
            "unity.ui": "ui.md",
            "unity.execution-path": "execution_path.md",
            "unity.data-contracts": "data_contracts.md",
            "unity.graphics-platform": "graphics_platform.md",
            "unity.architecture-patterns": "architecture_patterns.md",
        }
        rules_dir = Path(__file__).parent.parent / "rules"
        parts = []
        for name in rule_names:
            filename = rule_map.get(name)
            if not filename:
                continue
            rule_path = rules_dir / filename
            if rule_path.exists():
                content = rule_path.read_text(encoding="utf-8").strip()
                parts.append(content)
        return "\n\n---\n\n".join(parts)

    def _parse_file_changes(self, agent_output: str) -> list[dict]:
        """Parse file changes from agent output."""
        changes = []
        pattern = re.compile(
            r"(?:FILE|file|File):\s*(.+?)\n"
            r"(?:ACTION|action|Action):\s*(.+?)\n"
            r"(?:CONTENT|content|Content):\s*(.+?)(?=\n(?:FILE|file|File):|\Z)",
            re.DOTALL,
        )
        for match in pattern.finditer(agent_output):
            changes.append(
                {
                    "path": match.group(1).strip(),
                    "action": match.group(2).strip(),
                    "content": match.group(3).strip(),
                }
            )
        return changes
