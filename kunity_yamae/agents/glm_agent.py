"""GLM (Zhipu) agent adapter."""

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from ..ledger import EvidenceLedger
from .base import BaseAgent


class GlmAgent(BaseAgent):
    def execute(
        self, task: str, project_path: Path, risk_report: dict, mode: str, ledger: EvidenceLedger
    ) -> dict:
        api_key = os.environ.get(self.agent_config.get("api_key_env", "ZHIPU_API_KEY"), "")
        if not api_key:
            return {"status": "error", "message": "ZHIPU_API_KEY not set"}

        max_retries = self.agent_config.get("max_retries", 3)
        endpoint = self.agent_config.get(
            "endpoint", "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        )
        timeout = self.agent_config.get("timeout", 120)

        for attempt in range(max_retries):
            try:
                prompt = self._build_prompt(task, risk_report, mode, project_path)
                model = self.agent_config.get("model", "glm-4-plus")
                payload = json.dumps(
                    {
                        "model": model,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are a Unity C# expert working within "
                                    "K-Unity-Yamae harness."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": self.agent_config.get("temperature", 0.2),
                    }
                ).encode("utf-8")

                req = urllib.request.Request(
                    endpoint,
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    result_text = data["choices"][0]["message"]["content"]

                changes = self._parse_file_changes(result_text)
                ledger.add_event(
                    "agent_output",
                    {"agent": "glm", "preview": result_text[:500], "changes": len(changes)},
                )
                return {"status": "completed", "output": result_text, "changes": changes}
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503) and attempt < max_retries - 1:
                    time.sleep(2**attempt)
                    continue
                return {"status": "error", "message": f"HTTP {e.code}: {e.reason}"}
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)
                    continue
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Max retries exceeded"}
