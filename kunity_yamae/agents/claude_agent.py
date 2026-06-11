"""Claude (Anthropic) agent adapter."""

import os
import time
from pathlib import Path

from ..ledger import EvidenceLedger
from .base import BaseAgent


class ClaudeAgent(BaseAgent):
    def execute(
        self, task: str, project_path: Path, risk_report: dict, mode: str, ledger: EvidenceLedger
    ) -> dict:
        api_key = os.environ.get(self.agent_config.get("api_key_env", "ANTHROPIC_API_KEY"), "")
        if not api_key:
            return {"status": "error", "message": "ANTHROPIC_API_KEY not set"}

        max_retries = self.agent_config.get("max_retries", 3)
        max_tokens = self.agent_config.get("max_tokens", 16384)
        temperature = self.agent_config.get("temperature", 0.2)

        for attempt in range(max_retries):
            try:
                from anthropic import Anthropic, APIConnectionError, APITimeoutError, RateLimitError

                client = Anthropic(api_key=api_key, timeout=120)
                prompt = self._build_prompt(task, risk_report, mode, project_path)
                response = client.messages.create(
                    model=self.agent_config.get("model", "claude-sonnet-4-20250514"),
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=(
                        "You are a Unity C# expert working within K-Unity-Yamae "
                        "harness. Follow the rules in the prompt precisely."
                    ),
                    messages=[{"role": "user", "content": prompt}],
                )
                if not response.content:
                    return {"status": "error", "message": "Empty response from model"}
                result_text = response.content[0].text
                changes = self._parse_file_changes(result_text)
                ledger.add_event(
                    "agent_output",
                    {"agent": "claude", "preview": result_text[:500], "changes": len(changes)},
                )
                return {"status": "completed", "output": result_text, "changes": changes}
            except (RateLimitError, APITimeoutError, APIConnectionError) as e:
                if attempt < max_retries - 1:
                    wait = 2**attempt
                    time.sleep(wait)
                    continue
                return {"status": "error", "message": f"API error after {max_retries} retries: {e}"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Max retries exceeded"}
