"""asmdef graph guard - detects assembly definition changes and their impact."""

import json
from pathlib import Path


class AsmdefGuard:
    def __init__(self, project_path: Path, config: dict):
        self.project_path = project_path
        self.config = config

    def check(self, changed_files: list[str], all_assemblies: list[dict] = None) -> list[dict]:
        """Check assembly definition changes for graph impact."""
        issues = []
        asmdef_changes = [
            f for f in changed_files if f.endswith(".asmdef") or f.endswith(".asmref")
        ]

        if not asmdef_changes:
            return issues

        assemblies = all_assemblies or self._load_all_assemblies()

        for asmdef_path in asmdef_changes:
            try:
                full_path = self.project_path / asmdef_path
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            issues.extend(self._check_editor_runtime_cross_ref(data, assemblies))
            issues.extend(self._check_platform_changes(data))
            issues.extend(self._check_define_constraints(data))
            issues.extend(self._check_unsafe_code(data))
            issues.extend(self._check_auto_referenced(data))

        return issues

    def _check_editor_runtime_cross_ref(
        self, asmdef_data: dict, assemblies: list[dict]
    ) -> list[dict]:
        issues = []
        asm_name = asmdef_data.get("name", "")
        is_editor = asmdef_data.get("includePlatforms") == ["Editor"]

        if is_editor:
            for other in assemblies:
                if other["name"] == asm_name:
                    continue
                if other.get("platform") == "runtime" and asm_name in other.get("references", []):
                    issues.append(
                        {
                            "guard": "asmdef_graph",
                            "severity": "hard_failure",
                            "file": asmdef_data.get("path", ""),
                            "message": (
                                f"Runtime assembly '{other['name']}' references "
                                f"Editor assembly '{asm_name}'."
                            ),
                        }
                    )
        return issues

    def _check_platform_changes(self, asmdef_data: dict) -> list[dict]:
        issues = []
        include = asmdef_data.get("includePlatforms", [])
        exclude = asmdef_data.get("excludePlatforms", [])
        if include and exclude:
            issues.append(
                {
                    "guard": "asmdef_graph",
                    "severity": "warning",
                    "file": asmdef_data.get("path", ""),
                    "message": (
                        f"Assembly '{asmdef_data.get('name', '')}' has both "
                        "include and exclude platforms. "
                        f"Included: {include}, Excluded: {exclude}."
                    ),
                }
            )
        return issues

    def _check_define_constraints(self, asmdef_data: dict) -> list[dict]:
        issues = []
        constraints = asmdef_data.get("defineConstraints", [])
        if constraints:
            issues.append(
                {
                    "guard": "asmdef_graph",
                    "severity": "info",
                    "file": asmdef_data.get("path", ""),
                    "message": (
                        f"Assembly '{asmdef_data.get('name', '')}' has define "
                        f"constraints: {constraints}."
                    ),
                }
            )
        return issues

    def _check_unsafe_code(self, asmdef_data: dict) -> list[dict]:
        issues = []
        if asmdef_data.get("allowUnsafeCode"):
            issues.append(
                {
                    "guard": "asmdef_graph",
                    "severity": "warning",
                    "file": asmdef_data.get("path", ""),
                    "message": f"Assembly '{asmdef_data.get('name', '')}' allows unsafe code.",
                }
            )
        return issues

    def _check_auto_referenced(self, asmdef_data: dict) -> list[dict]:
        issues = []
        if not asmdef_data.get("autoReferenced", True):
            issues.append(
                {
                    "guard": "asmdef_graph",
                    "severity": "info",
                    "file": asmdef_data.get("path", ""),
                    "message": f"Assembly '{asmdef_data.get('name', '')}' is not auto-referenced.",
                }
            )
        return issues

    def _load_all_assemblies(self) -> list[dict]:
        assemblies = []
        for asmdef in self.project_path.rglob("*.asmdef"):
            try:
                with open(asmdef, "r", encoding="utf-8") as f:
                    data = json.load(f)
                rel = str(asmdef.relative_to(self.project_path))
                assemblies.append(
                    {
                        "name": data.get("name", asmdef.stem),
                        "path": rel,
                        "platform": "editor"
                        if data.get("includePlatforms") == ["Editor"]
                        else "runtime",
                        "references": data.get("references", []),
                    }
                )
            except (json.JSONDecodeError, OSError):
                continue
        return assemblies

    def get_graph_impact(self, changed_asmdef: str, assemblies: list[dict] = None) -> dict:
        """Report the graph impact of changing an assembly definition."""
        assemblies = assemblies or self._load_all_assemblies()
        asm_data = next((a for a in assemblies if a["path"] == changed_asmdef), None)
        if not asm_data:
            return {"affected": [], "direct_refs": [], "transitive_refs": []}

        asm_name = asm_data["name"]
        direct_refs = [a["name"] for a in assemblies if asm_name in a.get("references", [])]
        transitive = set()
        queue = list(direct_refs)
        seen = set()
        while queue:
            current = queue.pop(0)
            if current in seen:
                continue
            seen.add(current)
            for a in assemblies:
                if current in a.get("references", []) and a["name"] not in transitive:
                    transitive.add(a["name"])
                    queue.append(a["name"])

        return {
            "assembly": asm_name,
            "direct_refs": direct_refs,
            "transitive_refs": list(transitive),
            "total_affected": len(direct_refs) + len(transitive),
        }
