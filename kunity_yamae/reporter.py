"""Completion report writer - produces structured final reports."""

import json
from pathlib import Path


class ReportWriter:
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.reports_dir = project_path / ".unity-harness" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def write_report(
        self, ledger_events: list[dict], risk_report: dict, task: str, mode: str
    ) -> str:
        """Write a completion report from ledger events and risk report."""
        report = self._build_report(ledger_events, risk_report, task, mode)
        md_content = self._render_markdown(report)
        json_content = json.dumps(report, indent=2)

        from datetime import datetime, timezone

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
        slug = task[:50].replace(" ", "-").replace("/", "-").lower()
        slug = "".join(c for c in slug if c.isalnum() or c == "-")

        md_path = self.reports_dir / f"{ts}-{slug}.report.md"
        json_path = self.reports_dir / f"{ts}-{slug}.report.json"

        md_path.write_text(md_content, encoding="utf-8")
        json_path.write_text(json_content, encoding="utf-8")

        return str(md_path)

    def _build_report(self, events: list[dict], risk_report: dict, task: str, mode: str) -> dict:
        changed_files = []
        guards_run = []
        verification_results = []
        manual_checks = []
        errors = []

        for event in events:
            evt_type = event.get("event", "")
            if evt_type == "file_changed":
                changed_files.append(
                    {"path": event.get("path", ""), "reason": event.get("reason", "")}
                )
            elif evt_type == "guard_result":
                guards_run.append(
                    {
                        "guard": event.get("guard", ""),
                        "result": event.get("status", ""),
                        "details": event.get("details", ""),
                    }
                )
            elif evt_type == "verification_tier":
                verification_results.append(
                    {
                        "tier": event.get("tier", ""),
                        "name": event.get("name", ""),
                        "result": event.get("status", ""),
                    }
                )
            elif evt_type == "manual_check":
                manual_checks.append(
                    {"item": event.get("item", ""), "status": event.get("status", "")}
                )
            elif evt_type == "agent_error":
                errors.append(event.get("error", ""))

        terminal_status = "incomplete"
        if any(e.get("event") == "task_completed" for e in events):
            terminal_status = "completed"
        elif any(e.get("event") == "task_failed" for e in events):
            terminal_status = "failed"
        elif any(e.get("event") == "task_blocked" for e in events):
            terminal_status = "blocked"
        max_tier = max((v["tier"] for v in verification_results), default="0")

        return {
            "summary": {
                "task": task,
                "mode": mode,
                "risk_score": risk_report.get("risk_score", 0),
                "status": terminal_status,
                "verification_tier": max_tier,
            },
            "changed_files": changed_files,
            "risk_decisions": {
                "serialized_data_impact": any(
                    "serialized" in t.lower() for t in risk_report.get("triggers", [])
                ),
                "meta_guid_impact": any(
                    "meta" in t.lower() or "guid" in t.lower()
                    for t in risk_report.get("triggers", [])
                ),
                "yaml_impact": any("yaml" in t.lower() for t in risk_report.get("triggers", [])),
                "editor_runtime_impact": any(
                    "editor" in t.lower() for t in risk_report.get("triggers", [])
                ),
                "resources_addressables_impact": any(
                    "resources" in t.lower() or "addressable" in t.lower()
                    for t in risk_report.get("triggers", [])
                ),
            },
            "guards_run": guards_run,
            "verification": verification_results,
            "manual_checks": manual_checks,
            "errors": errors,
            "known_limitations": self._identify_limitations(verification_results, mode),
        }

    def _render_markdown(self, report: dict) -> str:
        lines = ["# K-Unity-Yamae Completion Report", ""]
        s = report["summary"]
        lines.extend(
            [
                "## Summary",
                f"- **Task**: {s['task']}",
                f"- **Mode**: {s['mode']}",
                f"- **Risk score**: {s['risk_score']}",
                f"- **Status**: {s['status']}",
                f"- **Verification tier**: {s['verification_tier']}",
                "",
            ]
        )

        if report["changed_files"]:
            lines.append("## Changed files")
            lines.append("| File | Reason |")
            lines.append("| --- | --- |")
            for f in report["changed_files"]:
                lines.append(f"| {f['path']} | {f['reason']} |")
            lines.append("")

        lines.append("## Unity risk decisions")
        rd = report["risk_decisions"]
        for key, val in rd.items():
            label = key.replace("_", " ").title()
            lines.append(f"- **{label}**: {'Yes' if val else 'No'}")
        lines.append("")

        if report["guards_run"]:
            lines.append("## Guards run")
            lines.append("| Guard | Result | Notes |")
            lines.append("| --- | --- | --- |")
            for g in report["guards_run"]:
                lines.append(f"| {g['guard']} | {g['result']} | {g['details']} |")
            lines.append("")

        if report["verification"]:
            lines.append("## Verification actually run")
            lines.append("| Tier | Check | Result |")
            lines.append("| --- | --- | --- |")
            for v in report["verification"]:
                lines.append(f"| {v['tier']} | {v['name']} | {v['result']} |")
            lines.append("")

        if report["manual_checks"]:
            lines.append("## Manual checks still required")
            for mc in report["manual_checks"]:
                lines.append(f"- [ ] {mc['item']}")
            lines.append("")

        if report["errors"]:
            lines.append("## Errors")
            for err in report["errors"]:
                lines.append(f"- {err}")
            lines.append("")

        if report["known_limitations"]:
            lines.append("## Known limitations")
            for lim in report["known_limitations"]:
                lines.append(f"- {lim}")
            lines.append("")

        tier = report["summary"]["verification_tier"]
        lines.extend(
            [
                "## Final statement",
                f"This task is complete to verification tier **{tier}**. "
                "It is not fully Editor/PlayMode/build verified unless those "
                "tiers are listed as passed above.",
            ]
        )

        return "\n".join(lines)

    def _identify_limitations(self, verification_results: list[dict], mode: str) -> list[str]:
        limitations = []
        verified_tiers = {v["tier"] for v in verification_results if v["result"] == "passed"}
        if "1" not in verified_tiers:
            limitations.append("Unity compile/import was not verified.")
        if "2" not in verified_tiers and mode in ("asset_safe", "migration"):
            limitations.append("EditMode tests were not run.")
        if "3" not in verified_tiers and mode == "migration":
            limitations.append("PlayMode tests were not run.")
        if "5" not in verified_tiers and mode == "migration":
            limitations.append("Build validation was not run.")
        if mode in ("asset_safe", "migration"):
            limitations.append("Manual Inspector/scene/prefab verification may still be required.")
        return limitations

    def read_last_ledger(self) -> list[dict] | None:
        """Read the last ledger file."""
        ledger_path = self.project_path / ".unity-harness" / "last-ledger.jsonl"
        if not ledger_path.exists():
            return None
        events = []
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
        return events if events else None

    def print_report(self, ledger_events: list[dict]):
        """Print a human-readable report from ledger events."""
        for e in ledger_events:
            if e.get("event") == "task_started":
                continue
            elif e.get("event") == "file_changed":
                print(f"  Changed: {e.get('path', '')} ({e.get('reason', '')})")
            elif e.get("event") == "guard_result":
                status = e.get("status", "")
                print(f"  Guard {e.get('guard', '')}: {status} - {e.get('details', '')}")
            elif e.get("event") == "verification_tier":
                print(
                    f"  Verification tier {e.get('tier', '')} "
                    f"({e.get('name', '')}): {e.get('status', '')}"
                )
            elif e.get("event") == "manual_check":
                print(f"  Manual check: {e.get('item', '')} [{e.get('status', '')}]")
