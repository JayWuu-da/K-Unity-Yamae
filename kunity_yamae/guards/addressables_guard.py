"""Resources and Addressables guard - detects string-key asset path changes."""

import re
from pathlib import Path


class AddressablesGuard:
    def __init__(self, project_path: Path, config: dict):
        self.project_path = project_path
        self.config = config

    def check(self, changed_files: list[str], diff_content: str = "") -> list[dict]:
        """Check for Resources/Addressables string-key path changes."""
        issues = []

        if diff_content:
            issues.extend(self._check_diff_for_resources(diff_content))
            issues.extend(self._check_diff_for_addressables(diff_content))

        for f in changed_files:
            if f.startswith("Assets/") and "/Resources/" in f:
                issues.append(
                    {
                        "guard": "resources_addressables",
                        "severity": "warning",
                        "file": f,
                        "message": f"File under Resources folder: {f}. "
                        "Will be included in build and loaded by string key.",
                    }
                )

        return issues

    def _check_diff_for_resources(self, diff_content: str) -> list[dict]:
        issues = []
        pattern = re.compile(r'Resources\.Load\s*\(\s*@"?([^"]+)"?\s*\)', re.MULTILINE)
        for match in pattern.finditer(diff_content):
            path = match.group(1)
            asset_path = self.project_path / "Assets" / "Resources" / f"{path}.asset"
            cs_search = list(self.project_path.rglob(f"{path}.*"))
            if not asset_path.exists() and not cs_search:
                issues.append(
                    {
                        "guard": "resources_addressables",
                        "severity": "warning",
                        "file": "",
                        "message": (
                            f"Resources.Load path '{path}' may not exist. "
                            "Verify asset is in a Resources folder."
                        ),
                    }
                )
        return issues

    def _check_diff_for_addressables(self, diff_content: str) -> list[dict]:
        issues = []
        key_pattern = re.compile(
            r'Addressables\.LoadAssetAsync\s*<?\w*>?\s*\(\s*@"?([^"]+)"?\s*\)', re.MULTILINE
        )
        for match in key_pattern.finditer(diff_content):
            key = match.group(1)
            issues.append(
                {
                    "guard": "resources_addressables",
                    "severity": "info",
                    "file": "",
                    "message": (
                        f"Addressables key '{key}' referenced. "
                        "Verify key exists in Addressables groups."
                    ),
                }
            )

        label_pattern = re.compile(
            r'Addressables\.LabelExists\s*\(\s*@"?([^"]+)"?\s*\)', re.MULTILINE
        )
        for match in label_pattern.finditer(diff_content):
            label = match.group(1)
            issues.append(
                {
                    "guard": "resources_addressables",
                    "severity": "info",
                    "file": "",
                    "message": f"Addressables label '{label}' referenced. Verify label exists.",
                }
            )

        return issues

    def check_scene_name_change(self, diff_content: str) -> list[dict]:
        issues = []
        build_settings_pattern = re.compile(r"^[\+\-].*path:\s*(.+\.unity)", re.MULTILINE)
        for match in build_settings_pattern.finditer(diff_content):
            line = match.group(0)
            scene_path = match.group(1).strip().strip('"')
            if line.startswith("+"):
                issues.append(
                    {
                        "guard": "resources_addressables",
                        "severity": "info",
                        "file": "ProjectSettings/EditorBuildSettings.asset",
                        "message": f"Scene '{scene_path}' added to build settings.",
                    }
                )
            elif line.startswith("-"):
                issues.append(
                    {
                        "guard": "resources_addressables",
                        "severity": "warning",
                        "file": "ProjectSettings/EditorBuildSettings.asset",
                        "message": f"Scene '{scene_path}' removed from build settings.",
                    }
                )
        return issues
