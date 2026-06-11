"""Risk classifier for Unity tasks."""

import re


class RiskClassifier:
    def __init__(self, config: dict):
        self.config = config
        self.risk_config = config.get("risk", {})
        self.file_risk_scores = config.get("file_risk_scores", {})

    def classify(self, task: str, profile: dict, diff: str = "") -> dict:
        """Classify a task's Unity risk and return a risk report."""
        triggers = []
        file_risk = 0
        action_risk = 0
        semantic_risk = 0

        task_lower = task.lower()

        semantic_risk += self._check_serialized_field_rename(task_lower, triggers)
        semantic_risk += self._check_monoBehaviour_lifecycle(task_lower, triggers)
        semantic_risk += self._check_editor_runtime_boundary(task_lower, triggers)
        semantic_risk += self._check_resources_addressables(task_lower, triggers)
        semantic_risk += self._check_ui_interaction(task_lower, triggers)
        semantic_risk += self._check_execution_path(task_lower, triggers)
        semantic_risk += self._check_data_contract(task_lower, triggers)
        semantic_risk += self._check_graphics_platform(task_lower, triggers)
        semantic_risk += self._check_architecture_pattern(task_lower, triggers)
        semantic_risk += self._check_asmdef_change(task_lower, triggers)
        semantic_risk += self._check_package_settings(task_lower, triggers)
        semantic_risk += self._check_asset_move(task_lower, triggers)
        semantic_risk += self._check_yaml_edit(task_lower, triggers)

        action_risk += self._classify_action(task_lower, triggers)

        if diff:
            file_risk += self._classify_diff_risk(diff, triggers)

        total_risk = min(100, file_risk + action_risk + semantic_risk)
        mode = self._select_mode(total_risk)

        blocked_ops = self._get_blocked_operations(mode)
        required_rules = self._select_rule_cards(triggers)
        required_verification = self._select_verification(mode)

        return {
            "schema": "unity-harness.risk-report.v1",
            "task": task,
            "risk_score": total_risk,
            "mode": mode,
            "triggers": triggers,
            "required_rule_cards": required_rules,
            "blocked_operations": blocked_ops,
            "required_verification": required_verification,
            "rationale": self._generate_rationale(total_risk, mode, triggers),
        }

    def _check_serialized_field_rename(self, task_lower: str, triggers: list) -> int:
        rename_patterns = [
            r"rename\s+\w+\.\w+\s+to\s+\w+",
            r"rename\s+\w+\s+to\s+\w+",
            r"change\s+\w+\s+field\s+\w+\s+to\s+\w+",
            r"field\s+\w+\s+rename",
            r"serialized\s+field\s+rename",
        ]
        for pattern in rename_patterns:
            if re.search(pattern, task_lower):
                triggers.append("Serialized field/class rename (asmdef risk)")
                return 70
        return 0

    def _check_monoBehaviour_lifecycle(self, task_lower: str, triggers: list) -> int:
        lifecycle_methods = [
            "awake",
            "onenable",
            "start",
            "update",
            "fixedupdate",
            "lateupdate",
            "ondisable",
            "ondestroy",
            "onvalidate",
            "reset",
        ]
        for method in lifecycle_methods:
            if method in task_lower:
                triggers.append(f"MonoBehaviour lifecycle ({method})")
                return 20
        lifecycle_behaviors = [
            "spawn",
            "wait",
            "coroutine",
            "invoke",
            "timer",
            "delay",
            "interval",
            "loop",
            "callback",
        ]
        for behavior in lifecycle_behaviors:
            if behavior in task_lower:
                triggers.append(f"MonoBehaviour behavior ({behavior})")
                return 25
        return 0

    def _check_editor_runtime_boundary(self, task_lower: str, triggers: list) -> int:
        editor_keywords = [
            "editor script",
            "custom inspector",
            "editor window",
            "property drawer",
            "editor utility",
            "unityeditor",
        ]
        for kw in editor_keywords:
            if kw in task_lower:
                triggers.append("Editor/runtime boundary")
                return 25
        return 0

    def _check_resources_addressables(self, task_lower: str, triggers: list) -> int:
        if "resources.load" in task_lower or "addressable" in task_lower:
            triggers.append("Resources/Addressables path change")
            return 30
        return 0

    def _check_ui_interaction(self, task_lower: str, triggers: list) -> int:
        keywords = ["ui", "button", "onclick", "canvas", "raycast", "eventsystem", "recttransform"]
        if any(keyword in task_lower for keyword in keywords):
            triggers.append("Unity UI interaction/hierarchy")
            return 25
        return 0

    def _check_execution_path(self, task_lower: str, triggers: list) -> int:
        keywords = [
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
        ]
        if self._has_task_keyword(task_lower, keywords):
            triggers.append("Unity execution path tracing")
            return 20
        return 0

    def _check_data_contract(self, task_lower: str, triggers: list) -> int:
        keywords = [
            "table",
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
        ]
        if self._has_task_keyword(task_lower, keywords):
            triggers.append("Unity data contract/payload")
            return 30
        return 0

    def _check_graphics_platform(self, task_lower: str, triggers: list) -> int:
        keywords = [
            "texture",
            "compression",
            "astc",
            "etc2",
            "ios",
            "android",
            "pc",
            "shader",
            "mipmap",
        ]
        if any(keyword in task_lower for keyword in keywords):
            triggers.append("Graphics/import platform settings")
            return 35
        return 0

    def _check_architecture_pattern(self, task_lower: str, triggers: list) -> int:
        keywords = [
            "mvp",
            "mvc",
            "presenter",
            "controller",
            "game manager",
            "eventbus",
            "service",
        ]
        if any(keyword in task_lower for keyword in keywords):
            triggers.append("Unity architecture pattern")
            return 20
        return 0

    def _check_asmdef_change(self, task_lower: str, triggers: list) -> int:
        if "asmdef" in task_lower or "assembly definition" in task_lower:
            triggers.append("Assembly definition (asmdef) change")
            return 50
        return 0

    def _check_package_settings(self, task_lower: str, triggers: list) -> int:
        package_action = any(word in task_lower for word in ["upgrade", "update", "add"])
        if "package" in task_lower and package_action:
            triggers.append("Package change")
            return 45
        if "projectsettings" in task_lower or "project settings" in task_lower:
            triggers.append("ProjectSettings change")
            return 45
        return 0

    def _check_asset_move(self, task_lower: str, triggers: list) -> int:
        move_patterns = [
            r"move\s+\w+\s+(to|into)",
            r"relocate",
            r"reorganize.*folder",
            r"move.*prefab",
            r"move.*asset",
            r"move.*scene",
        ]
        for pattern in move_patterns:
            if re.search(pattern, task_lower):
                triggers.append("Asset move/rename")
                return 50
        return 0

    def _check_yaml_edit(self, task_lower: str, triggers: list) -> int:
        yaml_patterns = [
            r"edit\s+.*\.(unity|prefab|asset|controller|anim)",
            r"yaml\s+(edit|write|modify)",
            r"direct.*yaml",
        ]
        for pattern in yaml_patterns:
            if re.search(pattern, task_lower):
                triggers.append("Direct YAML edit")
                return 55
        return 0

    def _classify_action(self, task_lower: str, triggers: list) -> int:
        if any(w in task_lower for w in ["fix", "bug", "typo", "null check"]):
            return 5
        if any(w in task_lower for w in ["add", "create", "implement", "write"]):
            return 15
        if any(w in task_lower for w in ["refactor", "restructure", "reorganize"]):
            return 25
        return 10

    def _classify_diff_risk(self, diff: str, triggers: list) -> int:
        risk = 0
        if ".meta" in diff:
            triggers.append("Diff touches .meta files")
            risk += 60
        if ".unity" in diff or ".prefab" in diff:
            triggers.append("Diff touches scene/prefab files")
            risk += 50
        if ".asmdef" in diff:
            triggers.append("Diff touches assembly definitions")
            risk += 40
        if "[SerializeField]" in diff or "[SerializeReference]" in diff:
            triggers.append("Diff modifies serialized fields")
            risk += 35
        if "FormerlySerializedAs" in diff:
            triggers.append("Diff adds migration attributes")
            risk += 20
        return risk

    def _select_mode(self, risk_score: int) -> str:
        if risk_score <= self.risk_config.get("low_max", 29):
            return "fast_patch"
        elif risk_score <= self.risk_config.get("standard_max", 59):
            return "standard"
        elif risk_score <= self.risk_config.get("asset_safe_max", 79):
            return "asset_safe"
        else:
            return "migration"

    def _get_blocked_operations(self, mode: str) -> list[str]:
        protected = self.config.get("protected_files", {})
        block = protected.get("block_direct_write", [])
        if mode in ("fast_patch", "standard"):
            return block + protected.get("escalate_direct_write", [])
        if mode == "asset_safe":
            return block
        return []

    def _select_rule_cards(self, triggers: list[str]) -> list[str]:
        rules = ["unity.global"]
        trigger_rule_map = {
            "Serialized field/class rename": "unity.serialized-field-rename",
            "MonoBehaviour lifecycle": "unity.monobehaviour-lifecycle",
            "Editor/runtime boundary": "unity.editor-runtime-boundary",
            "Resources/Addressables path change": "unity.resources-addressables",
            "Unity UI interaction/hierarchy": "unity.ui",
            "Unity execution path tracing": "unity.execution-path",
            "Unity data contract/payload": "unity.data-contracts",
            "Graphics/import platform settings": "unity.graphics-platform",
            "Unity architecture pattern": "unity.architecture-patterns",
            "Assembly definition change": "unity.asmdef",
            "Asset move/rename": "unity.meta-guid",
            "Direct YAML edit": "unity.prefab-scene-yaml",
            "Diff touches .meta files": "unity.meta-guid",
            "Diff touches scene/prefab files": "unity.prefab-scene-yaml",
            "Diff modifies serialized fields": "unity.serialized-field-rename",
        }
        for trigger in triggers:
            for key, rule in trigger_rule_map.items():
                if key in trigger and rule not in rules:
                    rules.append(rule)
        return rules

    def _select_verification(self, mode: str) -> list[str]:
        verification = ["static guards"]
        if mode in ("standard", "asset_safe", "migration"):
            verification.append("Unity compile/import")
        if mode in ("asset_safe", "migration"):
            verification.extend(["EditMode tests", "PlayMode tests"])
        if mode == "migration":
            verification.append("Build validation")
        return verification

    def _generate_rationale(self, risk_score: int, mode: str, triggers: list[str]) -> str:
        lines = [f"Risk score {risk_score} -> {mode} mode."]
        if triggers:
            lines.append(f"Triggers: {', '.join(triggers[:5])}.")
        if risk_score < 30:
            lines.append("Low Unity-specific risk; fast patch appropriate.")
        elif risk_score < 60:
            lines.append("Moderate risk; standard verification recommended.")
        elif risk_score < 80:
            lines.append("Significant Unity risk; asset-safe guards required.")
        else:
            lines.append("High risk; migration-level guardrails and evidence required.")
        return " ".join(lines)

    @staticmethod
    def _has_task_keyword(task_lower: str, keywords: list[str]) -> bool:
        return any(
            re.search(rf"(?<![a-z0-9_]){re.escape(keyword)}(?![a-z0-9_])", task_lower)
            for keyword in keywords
        )
