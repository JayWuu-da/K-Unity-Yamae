"""OpenAI Codex agent adapter."""

import os
import time
from pathlib import Path

from ..ledger import EvidenceLedger
from .base import BaseAgent


class CodexAgent(BaseAgent):
    def execute(
        self, task: str, project_path: Path, risk_report: dict, mode: str, ledger: EvidenceLedger
    ) -> dict:
        api_key = os.environ.get(self.agent_config.get("api_key_env", "OPENAI_API_KEY"), "")
        if not api_key:
            return {"status": "error", "message": "OPENAI_API_KEY not set"}

        max_retries = self.agent_config.get("max_retries", 3)
        temperature = self.agent_config.get("temperature", 0.2)

        for attempt in range(max_retries):
            try:
                from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError

                client = OpenAI(api_key=api_key, timeout=120)
                prompt = self._build_prompt(task, risk_report, mode, project_path)
                response = client.chat.completions.create(
                    model=self.agent_config.get("model", "gpt-4o"),
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a Unity C# expert working within "
                                "K-Unity-Yamae harness. Follow the rules in "
                                "the prompt precisely."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=temperature,
                )
                result_text = response.choices[0].message.content
                if result_text is None:
                    return {"status": "error", "message": "Empty response from model"}
                changes = self._parse_file_changes(result_text)
                ledger.add_event(
                    "agent_output",
                    {"agent": "codex", "preview": result_text[:500], "changes": len(changes)},
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
