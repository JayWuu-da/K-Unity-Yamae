"""Evidence ledger - records what happened during a task."""

import json
from datetime import datetime, timezone
from pathlib import Path


class EvidenceLedger:
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.ledger_dir = project_path / ".unity-harness"
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self.events: list[dict] = []
        self._current_ledger_path = self.ledger_dir / "last-ledger.jsonl"

    def start_task(self, task: str, mode: str, risk_report: dict):
        """Record task start."""
        self.events = []
        self.add_event(
            "task_started",
            {
                "task": task,
                "mode": mode,
                "risk_score": risk_report.get("risk_score", 0),
                "triggers": risk_report.get("triggers", []),
            },
        )

    def add_event(self, event_type: str, data: dict):
        """Add an event to the ledger."""
        event = {
            "event": event_type,
            "utc": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self.events.append(event)
        with open(self._current_ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    def add_file_change(self, path: str, reason: str):
        self.add_event("file_changed", {"path": path, "reason": reason})

    def add_guard_result(self, guard: str, status: str, details: str = ""):
        self.add_event("guard_result", {"guard": guard, "status": status, "details": details})

    def add_verification(self, tier: str, name: str, status: str, log_path: str = ""):
        self.add_event(
            "verification_tier", {"tier": tier, "name": name, "status": status, "log": log_path}
        )

    def add_manual_check(self, item: str, status: str = "required"):
        self.add_event("manual_check", {"item": item, "status": status})

    def add_command(self, name: str, exit_code: int, log: str = ""):
        self.add_event("command", {"name": name, "exitCode": exit_code, "log": log})

    def finalize(self, status: str = "completed") -> str:
        event_type = "task_completed" if status == "completed" else f"task_{status}"
        self.add_event(event_type, {"status": status, "total_events": len(self.events)})
        return str(self._current_ledger_path)

    def get_events(self) -> list[dict]:
        return self.events.copy()

    def get_risk_report(self) -> dict | None:
        for event in self.events:
            if event.get("event") == "task_started":
                return {
                    "risk_score": event.get("risk_score", 0),
                    "triggers": event.get("triggers", []),
                    "mode": event.get("mode", ""),
                }
        return None
