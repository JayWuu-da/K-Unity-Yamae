"""Context selector - provides only relevant files and rule cards for a task."""

import re
from pathlib import Path

from .constants import GENERATED_FOLDERS
from .semantic_index import runtime_safety_hints
from .unity_profile import load_cached_profile


class ContextSelector:
    def __init__(self, project_path: Path, config: dict):
        self.project_path = project_path
        self.config = config
        ctx_config = config.get("context", {})
        self.max_memory_chars = ctx_config.get("max_memory_chars", 2000)
        self.max_preview_lines = ctx_config.get("max_preview_lines", 50)
        self.max_files = ctx_config.get("max_files", 10)
        self.max_file_size = ctx_config.get("max_file_size", 100000)

    def select(self, task: str, risk_report: dict, mode: str) -> dict:
        """Select relevant context for the task."""
        context = {
            "task_brief": task,
            "risk_report": risk_report,
            "mode": mode,
            "rule_cards": self._select_rule_cards(risk_report),
            "relevant_files": [],
            "summaries": [],
            "unity_facts": self._select_unity_facts(task),
            "manual_checks": self._manual_checks(task, risk_report),
            "project_memory": self._load_nearest_memory(task),
        }

        target_files = self._infer_target_files(task)
        for f in target_files:
            full_path = self.project_path / f
            if full_path.exists():
                context["relevant_files"].append(f)
                if f.endswith(".cs") and full_path.stat().st_size < self.max_file_size:
                    try:
                        content = full_path.read_text(encoding="utf-8")
                        context["summaries"].append(
                            {
                                "path": f,
                                "type": "csharp",
                                "lines": len(content.splitlines()),
                                "preview": "\n".join(
                                    content.splitlines()[: self.max_preview_lines]
                                ),
                            }
                        )
                    except OSError:
                        pass

        return context

    def _select_rule_cards(self, risk_report: dict) -> list[str]:
        return risk_report.get("required_rule_cards", ["unity.global"])

    def _select_unity_facts(self, task: str) -> dict:
        profile = load_cached_profile(self.project_path)
        fact_keys = ["render_pipeline", "input_system", "platform_targets", "asset_summary"]
        task_lower = task.lower()
        if any(token in task_lower for token in ["ui", "button", "onclick", "canvas", "raycast"]):
            fact_keys.append("ui_system")
        if any(
            token in task_lower for token in ["texture", "compression", "shader", "android", "ios"]
        ):
            fact_keys.append("graphics_defaults")
        if any(
            token in task_lower
            for token in [
                "mvp",
                "mvc",
                "presenter",
                "controller",
                "manager",
                "service",
                "architecture",
                "refactor",
            ]
        ):
            fact_keys.append("architecture_patterns")
        selected = {key: profile.get(key, {}) for key in fact_keys}
        selected["asset_summary"] = self._task_focused_asset_summary(
            task_lower,
            selected.get("asset_summary", {}),
            profile.get("vfx_semantics", {}),
        )
        if any(token in task_lower for token in ["vfx", "visual", "ability", "prefab"]):
            selected["vfx_semantics"] = profile.get("vfx_semantics", {})
        safety = runtime_safety_hints(task, self.project_path)
        if safety:
            selected["runtime_safety"] = safety
        return selected

    def _manual_checks(self, task: str, risk_report: dict) -> list[str]:
        task_lower = task.lower()
        checks = []
        if any(token in task_lower for token in ["ui", "button", "onclick", "canvas", "raycast"]):
            checks.append(
                "Verify EventSystem, GraphicRaycaster, interactable state, and raycast blockers."
            )
        if self._has_task_keyword(
            task_lower,
            [
                "route",
                "routing",
                "popup",
                "openpopup",
                "createpopup",
                "shortcut",
                "listener",
                "binding",
                "controller reset",
                "reset path",
                "tab",
                "lock condition",
            ],
        ):
            checks.append(
                "Trace the real user path before editing: entry point, open/create call, "
                "prefab or listener binding, controller reset, lock conditions, and final renderer."
            )
        if self._has_task_keyword(
            task_lower,
            [
                "table",
                "tables",
                "localization",
                "locale",
                "packet",
                "payload",
                "dto",
                "response",
                "contract",
                "server",
                "backend",
                "reward",
                "rewards",
                "merge",
            ],
        ):
            checks.append(
                "Verify source table rows, localization keys, displayed text, "
                "request/response DTOs, final payload shape, merge rules, and response apply path."
            )
        if any(token in task_lower for token in ["prefab", "scene", "hierarchy"]):
            checks.append(
                "Verify prefab overrides, missing scripts, active hierarchy, "
                "and serialized references."
            )
        if any(token in task_lower for token in ["texture", "compression", "android", "ios", "pc"]):
            checks.append(
                "Compare Android, iOS, and PC import overrides before recommending changes."
            )
        if risk_report.get("mode") in ("asset_safe", "migration"):
            checks.append(
                "Run Unity Editor/manual inspection before claiming visual or Inspector behavior."
            )
        if any(token in task_lower for token in ["vfx", "visual", "ability", "resources.load"]):
            checks.append(
                "Use Unity MCP for refresh, tests, Game View screenshot, hierarchy, "
                "and console checks."
            )
            checks.append(
                "Verify Resources.Load paths, transient VFX lifetime, spawn caps, "
                "recursion guards, and collider side effects."
            )
        return checks

    def _task_focused_asset_summary(
        self,
        task_lower: str,
        asset_summary: dict,
        vfx_semantics: dict,
    ) -> dict:
        compact = dict(asset_summary)
        prefabs = asset_summary.get("prefabs", [])
        if not isinstance(prefabs, list):
            compact["prefabs"] = []
            return compact
        focused = [
            prefab
            for prefab in prefabs
            if isinstance(prefab, str)
            and not prefab.startswith("Library/")
            and self._matches_task_asset(task_lower, prefab)
        ]
        if focused:
            compact["prefabs"] = focused[: self.max_files]
        else:
            compact["prefabs"] = [
                prefab
                for prefab in prefabs[: self.max_files]
                if isinstance(prefab, str) and not prefab.startswith("Library/")
            ]
        if vfx_semantics:
            compact["vfx_summary"] = vfx_semantics.get("summary", {})
        return compact

    @staticmethod
    def _matches_task_asset(task_lower: str, path: str) -> bool:
        path_lower = path.lower()
        task_tokens = {token for token in task_lower.replace("/", " ").split() if len(token) > 2}
        return any(token in path_lower for token in task_tokens)

    @staticmethod
    def _has_task_keyword(task_lower: str, keywords: list[str]) -> bool:
        return any(
            re.search(rf"(?<![a-z0-9_]){re.escape(keyword)}(?![a-z0-9_])", task_lower)
            for keyword in keywords
        )

    def _infer_target_files(self, task: str) -> list[str]:
        task_lower = task.lower()
        files = []
        for cs_file in self.project_path.rglob("*.cs"):
            if self._is_in_generated(cs_file):
                continue
            name = cs_file.stem.lower()
            words = set(task_lower.split())
            name_words = set(name.replace("_", " ").replace("-", " ").split())
            if words & name_words:
                files.append(str(cs_file.relative_to(self.project_path)))
        return files[: self.max_files]

    def _load_nearest_memory(self, task: str) -> str | None:
        candidates = [
            self.project_path / "AGENTS.md",
            self.project_path / "Assets" / "UNITY_AGENTS.md",
        ]
        for path in candidates:
            if path.exists():
                return path.read_text(encoding="utf-8")[: self.max_memory_chars]
        return None

    def _is_in_generated(self, path: Path) -> bool:
        parts = path.relative_to(self.project_path).parts
        return bool(GENERATED_FOLDERS & set(parts))
