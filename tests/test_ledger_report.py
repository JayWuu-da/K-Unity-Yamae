from pathlib import Path

from kunity_yamae.ledger import EvidenceLedger
from kunity_yamae.reporter import ReportWriter


def test_failed_provider_run_is_not_reported_completed(tmp_path: Path) -> None:
    ledger = EvidenceLedger(tmp_path)
    risk_report = {"risk_score": 10, "triggers": [], "mode": "fast_patch"}
    ledger.start_task("Fix typo", "fast_patch", risk_report)
    ledger.add_event("agent_error", {"error": "OPENAI_API_KEY not set"})

    ledger.finalize(status="failed")
    report = ReportWriter(tmp_path)._build_report(
        ledger.get_events(),
        risk_report,
        "Fix typo",
        "fast_patch",
    )

    assert report["summary"]["status"] == "failed"
    assert report["errors"] == ["OPENAI_API_KEY not set"]
