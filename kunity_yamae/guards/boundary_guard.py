"""Editor/runtime boundary checker - ensures UnityEditor stays out of runtime assemblies."""

import re
from pathlib import Path

from ..constants import EDITOR_ONLY_ATTRIBUTES


class BoundaryGuard:
    def __init__(self, project_path: Path, config: dict):
        self.project_path = project_path
        self.config = config

    def check_file(self, file_path: str, content: str, assemblies: list[dict] = None) -> list[dict]:
        """Check if a C# file violates Editor/runtime boundaries."""
        issues = []

        uses_editor_ns = bool(re.search(r"using\s+UnityEditor", content))
        uses_editor_fq = bool(re.search(r"UnityEditor\.\w+", content))
        has_editor_preprocessor = bool(re.search(r"#if\s+UNITY_EDITOR", content))
        in_editor_folder = "/Editor/" in file_path or "\\Editor\\" in file_path

        if (
            (uses_editor_ns or uses_editor_fq)
            and not in_editor_folder
            and not has_editor_preprocessor
        ):
            assembly = self._find_assembly(file_path, assemblies or [])
            if assembly and assembly.get("platform") == "runtime":
                issues.append(
                    {
                        "guard": "editor_runtime_boundary",
                        "severity": "hard_failure",
                        "file": file_path,
                        "message": (
                            "File uses UnityEditor but is in runtime assembly "
                            f"'{assembly['name']}'. Move to Editor folder/asmdef "
                            "or wrap in #if UNITY_EDITOR."
                        ),
                    }
                )
            elif not assembly:
                issues.append(
                    {
                        "guard": "editor_runtime_boundary",
                        "severity": "warning",
                        "file": file_path,
                        "message": (
                            "File uses UnityEditor. Ensure it's in an Editor "
                            "folder/asmdef or wrapped in #if UNITY_EDITOR."
                        ),
                    }
                )

        for attr in EDITOR_ONLY_ATTRIBUTES:
            pattern = rf"\[{attr}(?:\s*\(|\])"
            matches = re.findall(pattern, content)
            for match in matches:
                if not in_editor_folder and not has_editor_preprocessor:
                    assembly = self._find_assembly(file_path, assemblies or [])
                    if assembly and assembly.get("platform") == "runtime":
                        issues.append(
                            {
                                "guard": "editor_runtime_boundary",
                                "severity": "hard_failure",
                                "file": file_path,
                                "message": f"[{attr}] attribute in runtime assembly. "
                                f"Move to Editor folder/asmdef or wrap in #if UNITY_EDITOR.",
                            }
                        )
                        break

        return issues

    def check_asmdef(self, asmdef_data: dict, all_assemblies: list[dict]) -> list[dict]:
        """Check assembly definition for boundary violations."""
        issues = []
        asm_name = asmdef_data.get("name", "")

        if asmdef_data.get("includePlatforms") == ["Editor"]:
            for other in all_assemblies:
                if other["name"] == asm_name:
                    continue
                if other.get("platform") == "runtime" and asm_name in other.get("references", []):
                    issues.append(
                        {
                            "guard": "editor_runtime_boundary",
                            "severity": "hard_failure",
                            "file": asmdef_data.get("path", ""),
                            "message": (
                                f"Runtime assembly '{other['name']}' references "
                                f"Editor assembly '{asm_name}'."
                            ),
                        }
                    )

        refs = asmdef_data.get("references", [])
        for ref in refs:
            ref_asm = next((a for a in all_assemblies if a["name"] == ref), None)
            if ref_asm and ref_asm.get("platform") == "editor":
                if asmdef_data.get("includePlatforms") != ["Editor"]:
                    issues.append(
                        {
                            "guard": "editor_runtime_boundary",
                            "severity": "hard_failure",
                            "file": asmdef_data.get("path", ""),
                            "message": f"Assembly '{asm_name}' references Editor assembly '{ref}'.",
                        }
                    )

        return issues

    def _find_assembly(self, file_path: str, assemblies: list[dict]) -> dict | None:
        file_path_norm = file_path.replace("\\", "/")
        best = None
        best_depth = 0
        for asm in assemblies:
            asm_dir = asm["path"].replace("\\", "/").rsplit("/", 1)[0] if "/" in asm["path"] else ""
            if asm_dir and file_path_norm.startswith(asm_dir):
                depth = len(asm_dir.split("/"))
                if depth > best_depth:
                    best = asm
                    best_depth = depth
        return best
