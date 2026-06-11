"""Direct YAML write guard - blocks writes to protected Unity YAML artifacts."""

from pathlib import Path

PROTECTED_EXTENSIONS = {
    ".unity",
    ".prefab",
    ".asset",
    ".controller",
    ".anim",
    ".overrideController",
    ".playable",
}


class YamlGuard:
    def __init__(self, project_path: Path, config: dict):
        self.project_path = project_path
        self.config = config
        self.protected = set(config.get("protected_files", {}).get("block_direct_write", []))

    def check(self, changed_files: list[str], mode: str = "fast_patch") -> list[dict]:
        """Check if any protected YAML files are being written."""
        issues = []
        for f in changed_files:
            if not self._is_yaml_protected(f):
                continue
            if mode in ("asset_safe", "migration"):
                issues.append(
                    {
                        "guard": "yaml_write",
                        "severity": "warning",
                        "file": f,
                        "message": f"Direct YAML write to {Path(f).suffix} file in {mode} mode. "
                        "Prefer Editor API or manual Editor change.",
                    }
                )
            else:
                issues.append(
                    {
                        "guard": "yaml_write",
                        "severity": "hard_failure",
                        "file": f,
                        "message": (
                            f"Direct YAML write to {Path(f).suffix} file blocked "
                            f"in {mode} mode. Use Asset-Safe or Migration mode, "
                            "or use Editor API."
                        ),
                    }
                )
        return issues

    def check_diff_for_yaml_writes(self, diff_content: str, mode: str = "fast_patch") -> list[dict]:
        """Analyze git diff for YAML writes to protected Unity files."""
        issues = []
        import re

        blocks = re.split(r"^diff --git", diff_content, flags=re.MULTILINE)
        for block in blocks:
            if not block.strip():
                continue
            file_match = re.search(r"b/(.+)", block)
            if not file_match:
                continue
            file_path = file_match.group(1)
            if self._is_yaml_protected(file_path):
                added_lines = len(re.findall(r"^\+[^+]", block, re.MULTILINE))
                removed_lines = len(re.findall(r"^-[^-]", block, re.MULTILINE))
                if mode in ("asset_safe", "migration"):
                    issues.append(
                        {
                            "guard": "yaml_write",
                            "severity": "warning",
                            "file": file_path,
                            "message": (
                                f"YAML diff detected: +{added_lines}/-"
                                f"{removed_lines} lines. Verify object IDs, "
                                "GUIDs, components, and manual validation."
                            ),
                        }
                    )
                else:
                    issues.append(
                        {
                            "guard": "yaml_write",
                            "severity": "hard_failure",
                            "file": file_path,
                            "message": f"YAML write to protected file blocked. "
                            f"Detected +{added_lines}/-{removed_lines} line changes.",
                        }
                    )
        return issues

    def _is_yaml_protected(self, path: str) -> bool:
        ext = Path(path).suffix.lower()
        return ext in PROTECTED_EXTENSIONS
