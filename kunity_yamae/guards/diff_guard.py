"""Diff guard - inspects git diff for Unity-specific hazards."""

import json
import re
import subprocess
from pathlib import Path

from ..constants import GENERATED_FOLDERS
from .addressables_guard import AddressablesGuard
from .asmdef_guard import AsmdefGuard
from .boundary_guard import BoundaryGuard
from .meta_guard import MetaGuard
from .serialization_guard import SerializationGuard
from .yaml_guard import YamlGuard


class DiffGuard:
    def __init__(self, project_path: Path, config: dict):
        self.project_path = project_path
        self.config = config
        self.meta_guard = MetaGuard(project_path, config)
        self.yaml_guard = YamlGuard(project_path, config)
        self.serialization_guard = SerializationGuard(project_path, config)
        self.boundary_guard = BoundaryGuard(project_path, config)
        self.asmdef_guard = AsmdefGuard(project_path, config)
        self.addressables_guard = AddressablesGuard(project_path, config)

    def check(self, diff_content: str | None = None) -> list[dict]:
        """Run all guards against the current git diff."""
        all_issues = []

        meta_status_issues = self.meta_guard.check_from_git_status()
        all_issues.extend(meta_status_issues)

        if diff_content is None:
            diff_content = self._get_git_diff()

        status_changed_files = self.meta_guard.changed_files_from_git_status()
        if not diff_content.strip() and not status_changed_files:
            return all_issues

        changed_files = sorted(
            {*self._extract_changed_files(diff_content), *status_changed_files}
        )

        all_issues.extend(self.meta_guard.check_guid_continuity(diff_content))
        all_issues.extend(self.yaml_guard.check(changed_files))
        all_issues.extend(self.yaml_guard.check_diff_for_yaml_writes(diff_content))
        all_issues.extend(self.addressables_guard.check(changed_files, diff_content))
        all_issues.extend(self.addressables_guard.check_scene_name_change(diff_content))
        all_issues.extend(self._check_serialization_renames(changed_files))

        assemblies = self._load_assemblies()
        for f in changed_files:
            if f.endswith(".cs"):
                try:
                    content = (self.project_path / f).read_text(encoding="utf-8")
                    all_issues.extend(self.boundary_guard.check_file(f, content, assemblies))
                except OSError:
                    pass
            if f.endswith(".asmdef"):
                all_issues.extend(self.asmdef_guard.check([f], assemblies))

        return self._dedupe_issues(all_issues)

    def _get_git_diff(self) -> str:
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(self.project_path),
                timeout=30,
            )
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""

    def _extract_changed_files(self, diff_content: str) -> list[str]:
        files = set()
        for match in re.finditer(r"^diff --git a/(.+?) b/(.+?)$", diff_content, re.MULTILINE):
            files.add(match.group(2))
        return list(files)

    def _check_serialization_renames(self, changed_files: list[str]) -> list[dict]:
        issues = []
        for changed_file in changed_files:
            if not changed_file.endswith(".cs"):
                continue
            old_content = self._read_head_file(changed_file)
            new_path = self.project_path / changed_file
            if old_content is None or not new_path.exists():
                continue
            try:
                new_content = new_path.read_text(encoding="utf-8")
            except OSError:
                continue
            issues.extend(self.serialization_guard.check(old_content, new_content, changed_file))
        return issues

    def _read_head_file(self, file_path: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", "show", f"HEAD:{file_path}"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(self.project_path),
                timeout=30,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        if result.returncode != 0:
            return None
        return result.stdout

    def _dedupe_issues(self, issues: list[dict]) -> list[dict]:
        deduped = []
        seen = set()
        for issue in issues:
            key = (
                issue.get("guard"),
                issue.get("severity"),
                issue.get("file"),
                issue.get("old_name"),
                issue.get("new_name"),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(issue)
        return deduped

    def _load_assemblies(self) -> list[dict]:
        assemblies = []
        for asmdef in self.project_path.rglob("*.asmdef"):
            if any(
                part in GENERATED_FOLDERS for part in asmdef.relative_to(self.project_path).parts
            ):
                continue
            try:
                with open(asmdef, "r", encoding="utf-8") as f:
                    data = json.load(f)
                assemblies.append(
                    {
                        "name": data.get("name", asmdef.stem),
                        "path": str(asmdef.relative_to(self.project_path)),
                        "platform": "editor"
                        if data.get("includePlatforms") == ["Editor"]
                        else "runtime",
                        "references": data.get("references", []),
                    }
                )
            except (json.JSONDecodeError, OSError):
                continue
        return assemblies
