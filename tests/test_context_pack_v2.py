from pathlib import Path

from kunity_yamae.config import load_config
from kunity_yamae.context import ContextSelector
from kunity_yamae.risk import RiskClassifier
from kunity_yamae.scanner import UnityProjectScanner
from tests.fixtures.make_unity_project import create_ui_graphics_architecture_project


def test_context_pack_includes_only_task_relevant_final_facts(tmp_path: Path) -> None:
    create_ui_graphics_architecture_project(tmp_path)
    config = load_config(tmp_path)
    UnityProjectScanner(tmp_path, config).scan(deep=True)
    risk = RiskClassifier(config).classify("Fix ShopPresenter button onClick raycast issue", {})

    context = ContextSelector(tmp_path, config).select(
        "Fix ShopPresenter button onClick raycast issue",
        risk,
        "standard",
    )

    assert "ui_system" in context["unity_facts"]
    assert "architecture_patterns" in context["unity_facts"]
    assert "graphics_defaults" not in context["unity_facts"]
    assert "unity.ui" in context["rule_cards"]
    assert "unity.architecture-patterns" in context["rule_cards"]
