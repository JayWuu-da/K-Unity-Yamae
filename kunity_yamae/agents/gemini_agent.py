"""Google Gemini agent adapter."""

import os
import time
from pathlib import Path

from ..ledger import EvidenceLedger
from .base import BaseAgent


class GeminiAgent(BaseAgent):
    def execute(
        self, task: str, project_path: Path, risk_report: dict, mode: str, ledger: EvidenceLedger
    ) -> dict:
        api_key = os.environ.get(self.agent_config.get("api_key_env", "GOOGLE_API_KEY"), "")
        if not api_key:
            return {"status": "error", "message": "GOOGLE_API_KEY not set"}

        max_retries = self.agent_config.get("max_retries", 3)
        temperature = self.agent_config.get("temperature", 0.2)

        for attempt in range(max_retries):
            try:
                from google import genai

                client = genai.Client(api_key=api_key)
                prompt = self._build_prompt(task, risk_report, mode, project_path)
                response = client.models.generate_content(
                    model=self.agent_config.get("model", "gemini-2.5-flash"),
                    contents=prompt,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=(
                            "You are a Unity C# expert working within "
                            "K-Unity-Yamae harness."
                        ),
                        temperature=temperature,
                    ),
                )
                result_text = response.text
                if result_text is None:
                    return {"status": "error", "message": "Empty response from model"}
                changes = self._parse_file_changes(result_text)
                ledger.add_event(
                    "agent_output",
                    {"agent": "gemini", "preview": result_text[:500], "changes": len(changes)},
                )
                return {"status": "completed", "output": result_text, "changes": changes}
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)
                    continue
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Max retries exceeded"}
