"""Mode policy - selects harness mode based on risk score."""

from typing import Any


def select_mode(risk_score: int, config: dict[str, Any]) -> str:
    """Select harness mode from risk score and config thresholds."""
    risk = config.get("risk", {})
    if risk_score <= risk.get("low_max", 29):
        return "fast_patch"
    elif risk_score <= risk.get("standard_max", 59):
        return "standard"
    elif risk_score <= risk.get("asset_safe_max", 79):
        return "asset_safe"
    else:
        return "migration"


MODE_DESCRIPTIONS = {
    "fast_patch": "Fast Patch: minimal plan, quick C# edit, static guards only.",
    "standard": "Standard: short plan, relevant Unity rules, compile/import check.",
    "asset_safe": "Asset-Safe: plan required, protected-file guard active, verification required.",
    "migration": "Migration: detailed plan, rollback strategy, strong evidence required.",
    "validation_only": "Validation-only: no edits, only checks and report.",
}


def get_mode_description(mode: str) -> str:
    return MODE_DESCRIPTIONS.get(mode, f"Unknown mode: {mode}")


def get_mode_requirements(mode: str) -> dict[str, bool]:
    return {
        "plan_required": mode in ("asset_safe", "migration"),
        "protected_file_guard": mode in ("asset_safe", "migration"),
        "compile_check": mode in ("standard", "asset_safe", "migration"),
        "tests_required": mode in ("asset_safe", "migration"),
        "build_check": mode == "migration",
        "manual_check_required": mode in ("asset_safe", "migration"),
    }
