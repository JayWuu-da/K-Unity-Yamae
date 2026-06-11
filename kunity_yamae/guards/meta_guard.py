"""Meta pair and GUID guard - ensures .meta files stay paired with assets."""

import re
import subprocess
from pathlib import Path


class MetaGuard:
    def __init__(self, project_path: Path, config: dict):
        self.project_path = project_path
        self.config = config

    def check_from_git_status(self) -> list[dict]:
        """Check git status for .meta pairing issues."""
        issues = []
        status = self._get_git_status()
        if not status:
            return issues

        assets_added = []
        assets_deleted = []
        metas_added = []
        metas_deleted = []

        for file_path, change_type in status.items():
            if not self._is_under_assets(file_path):
                continue
            if self._is_generated(file_path):
                continue

            if file_path.endswith(".meta"):
                if change_type == "A":
                    metas_added.append(file_path)
                elif change_type == "D":
                    metas_deleted.append(file_path)
            else:
                if change_type == "A":
                    assets_added.append(file_path)
                elif change_type == "D":
                    assets_deleted.append(file_path)

        for asset in assets_added:
            meta = asset + ".meta"
            if meta not in metas_added and not (self.project_path / meta).exists():
                issues.append(
                    {
                        "guard": "meta_pair",
                        "severity": "hard_failure",
                        "file": asset,
                        "message": "Asset added without matching .meta file",
                    }
                )

        for asset in assets_deleted:
            meta = asset + ".meta"
            if meta not in metas_deleted:
                issues.append(
                    {
                        "guard": "meta_pair",
                        "severity": "warning",
                        "file": asset,
                        "message": "Asset deleted without deleting matching .meta file",
                    }
                )

        for meta in metas_deleted:
            asset = meta.replace(".meta", "")
            if asset not in assets_deleted:
                issues.append(
                    {
                        "guard": "meta_pair",
                        "severity": "warning",
                        "file": meta,
                        "message": ".meta deleted without deleting matching asset",
                    }
                )

        for meta in metas_added:
            asset = meta.replace(".meta", "")
            if asset not in assets_added and not (self.project_path / asset).exists():
                issues.append(
                    {
                        "guard": "meta_pair",
                        "severity": "hard_failure",
                        "file": meta,
                        "message": ".meta added without matching asset file",
                    }
                )

        return issues

    def changed_files_from_git_status(self) -> list[str]:
        status = self._get_git_status() or {}
        return [
            file_path
            for file_path in status
            if self._is_under_assets(file_path) and not self._is_generated(file_path)
        ]

    def check(self, changed_files: list[str]) -> list[dict]:
        """Check changed files for .meta pairing (fallback without git status)."""
        issues = []
        metas = [f for f in changed_files if f.endswith(".meta")]
        assets = [
            f
            for f in changed_files
            if not f.endswith(".meta") and self._is_under_assets(f) and not self._is_generated(f)
        ]

        for asset in assets:
            meta = asset + ".meta"
            if meta not in metas and not (self.project_path / meta).exists():
                issues.append(
                    {
                        "guard": "meta_pair",
                        "severity": "hard_failure",
                        "file": asset,
                        "message": "Asset without matching .meta file",
                    }
                )

        for meta in metas:
            asset = meta.replace(".meta", "")
            if asset not in assets and not (self.project_path / asset).exists():
                issues.append(
                    {
                        "guard": "meta_pair",
                        "severity": "warning",
                        "file": meta,
                        "message": ".meta file without matching asset",
                    }
                )

        return issues

    def check_guid_continuity(self, diff_content: str) -> list[dict]:
        """Check if GUIDs changed in .meta files within a diff."""
        issues = []
        blocks = re.split(r"^diff --git", diff_content, flags=re.MULTILINE)
        for block in blocks:
            if not block.strip():
                continue
            file_match = re.search(r"b/(.+\.meta)", block)
            if not file_match:
                continue
            file_path = file_match.group(1)

            old_guids = re.findall(r"^-.*guid:\s*([a-f0-9]{32})", block, re.MULTILINE)
            new_guids = re.findall(r"^\+.*guid:\s*([a-f0-9]{32})", block, re.MULTILINE)

            if old_guids and new_guids:
                for old_g, new_g in zip(old_guids, new_guids):
                    if old_g != new_g:
                        issues.append(
                            {
                                "guard": "guid_continuity",
                                "severity": "hard_failure",
                                "file": file_path,
                                "message": (
                                    f"GUID changed: {old_g} -> {new_g}. "
                                    "Breaks all asset references."
                                ),
                            }
                        )
            elif old_guids and not new_guids:
                for g in old_guids:
                    issues.append(
                        {
                            "guard": "guid_continuity",
                            "severity": "hard_failure",
                            "file": file_path,
                            "message": f"GUID {g} removed from .meta file",
                        }
                    )

        return issues

    def _get_git_status(self) -> dict[str, str] | None:
        """Get git status as {path: change_type}."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain", "-u"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(self.project_path),
                timeout=15,
            )
            if result.returncode != 0:
                return None
            status = {}
            for line in result.stdout.splitlines():
                if len(line) < 4:
                    continue
                file_path = line[3:].strip().strip('"')
                if line.startswith("?? "):
                    status[file_path] = "A"
                    continue
                change_type = line[0] if line[0] != " " else line[1]
                status[file_path] = change_type
            return status
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def _is_under_assets(self, path: str) -> bool:
        return path.startswith("Assets/") or path.startswith("Assets\\")

    def _is_generated(self, path: str) -> bool:
        parts = Path(path).parts
        generated = {"Library", "Temp", "Obj", "Logs", "Builds", "UserSettings"}
        return bool(generated & set(parts))
