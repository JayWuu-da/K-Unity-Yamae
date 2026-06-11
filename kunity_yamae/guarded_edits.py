import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .guards import DiffGuard


class GuardedEditError(RuntimeError):
    pass


class GuardedEditWorkflow:
    def __init__(self, project_path: Path, config: dict[str, Any]):
        self.project_path = project_path
        self.config = config

    def evaluate(self, patch_text: str) -> dict[str, Any]:
        if not patch_text.strip():
            raise GuardedEditError("Patch is empty.")
        self._require_git_repo()
        cleanup = {"worktree_removed": False, "rolled_back": False}
        with tempfile.TemporaryDirectory(prefix="kunity-yamae-edit-") as tmp:
            worktree_path = Path(tmp) / "worktree"
            self._run_git(["worktree", "add", "--detach", str(worktree_path), "HEAD"])
            result: dict[str, Any]
            try:
                check = self._run_git_apply(worktree_path, patch_text, check_only=True)
                if check.returncode != 0:
                    result = {
                        "status": "invalid_patch",
                        "applied": False,
                        "issues": [],
                        "error": check.stderr.strip() or check.stdout.strip(),
                    }
                else:
                    applied = self._run_git_apply(worktree_path, patch_text, check_only=False)
                    if applied.returncode != 0:
                        result = {
                            "status": "invalid_patch",
                            "applied": False,
                            "issues": [],
                            "error": applied.stderr.strip() or applied.stdout.strip(),
                        }
                    else:
                        issues = DiffGuard(worktree_path, self.config).check()
                        hard_failures = [
                            issue for issue in issues if issue.get("severity") == "hard_failure"
                        ]
                        result = {
                            "status": "blocked" if hard_failures else "ready_to_apply",
                            "applied": False,
                            "issues": issues,
                            "error": None,
                        }
            finally:
                removed = self._run_git(
                    ["worktree", "remove", "--force", str(worktree_path)],
                    check=False,
                )
                cleanup["worktree_removed"] = removed.returncode == 0 or not worktree_path.exists()
            result["cleanup"] = cleanup
            return result

    def apply(self, patch_text: str) -> dict[str, Any]:
        evaluation = self.evaluate(patch_text)
        if evaluation["status"] != "ready_to_apply":
            evaluation.setdefault("cleanup", {})["rolled_back"] = True
            return evaluation

        check = self._run_git_apply(self.project_path, patch_text, check_only=True)
        if check.returncode != 0:
            return {
                "status": "invalid_patch",
                "applied": False,
                "issues": [],
                "error": check.stderr.strip() or check.stdout.strip(),
                "cleanup": {**evaluation.get("cleanup", {}), "rolled_back": False},
            }
        applied = self._run_git_apply(self.project_path, patch_text, check_only=False)
        if applied.returncode != 0:
            return {
                "status": "invalid_patch",
                "applied": False,
                "issues": [],
                "error": applied.stderr.strip() or applied.stdout.strip(),
                "cleanup": {**evaluation.get("cleanup", {}), "rolled_back": False},
            }
        issues = DiffGuard(self.project_path, self.config).check()
        hard_failures = [issue for issue in issues if issue.get("severity") == "hard_failure"]
        if hard_failures:
            rollback = self._run_git_apply(self.project_path, patch_text, reverse=True)
            return {
                "status": "rolled_back",
                "applied": False,
                "issues": issues,
                "error": "Guard failed after applying patch.",
                "cleanup": {
                    **evaluation.get("cleanup", {}),
                    "rolled_back": rollback.returncode == 0,
                },
            }
        return {
            "status": "applied",
            "applied": True,
            "issues": issues,
            "error": None,
            "cleanup": {**evaluation.get("cleanup", {}), "rolled_back": False},
        }

    def _require_git_repo(self) -> None:
        self._run_git(["rev-parse", "--show-toplevel"])

    def _run_git(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args],
            cwd=self.project_path,
            text=True,
            capture_output=True,
            check=check,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )

    @staticmethod
    def _run_git_apply(
        cwd: Path,
        patch_text: str,
        *,
        check_only: bool = False,
        reverse: bool = False,
    ) -> subprocess.CompletedProcess:
        args = ["git", "apply"]
        if check_only:
            args.append("--check")
        if reverse:
            args.append("--reverse")
        return subprocess.run(
            args,
            cwd=cwd,
            input=patch_text,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
