from pathlib import Path

from ..ledger import EvidenceLedger
from .base import BaseAgent


class LocalPatchAgent(BaseAgent):
    def execute(
        self,
        task: str,
        project_path: Path,
        risk_report: dict,
        mode: str,
        ledger: EvidenceLedger,
    ) -> dict:
        patch_text = self.agent_config.get("patch", "")
        patch_file = self.agent_config.get("patch_file", "")
        if patch_file:
            patch_path = Path(patch_file)
            if not patch_path.is_absolute():
                patch_path = project_path / patch_path
            patch_text = patch_path.read_text(encoding="utf-8")
        if not str(patch_text).strip():
            return {"status": "error", "message": "local-patch requires patch or patch_file"}
        ledger.add_event("agent_output", {"agent": "local-patch", "preview": str(patch_text)[:500]})
        return {"status": "completed", "output": str(patch_text), "changes": []}
