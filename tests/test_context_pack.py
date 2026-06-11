import json
from pathlib import Path

from kunity_yamae.config import load_config
from kunity_yamae.context import ContextSelector
from kunity_yamae.risk import RiskClassifier
from kunity_yamae.scanner import UnityProjectScanner


def create_ui_project(project_path: Path) -> None:
    (project_path / "ProjectSettings").mkdir()
    (project_path / "ProjectSettings" / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 6000.4.0f1\n", encoding="utf-8"
    )
    (project_path / "Packages").mkdir()
    (project_path / "Packages" / "manifest.json").write_text(
        json.dumps({"dependencies": {"com.unity.ugui": "2.0.0"}}),
        encoding="utf-8",
    )
    (project_path / "Assets" / "UI").mkdir(parents=True)
    (project_path / "Assets" / "UI" / "ShopButton.prefab").write_text(
        "GameObject:\n  m_Name: ShopButton\nCanvas:\nGraphicRaycaster:\nm_OnClick:\n",
        encoding="utf-8",
    )


def test_context_pack_selects_ui_rules_and_unity_facts(tmp_path: Path) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)
    scanner = UnityProjectScanner(tmp_path, config)
    scanner.scan(deep=True)
    risk_report = RiskClassifier(config).classify("Fix UI button onClick raycast issue", {})

    context = ContextSelector(tmp_path, config).select(
        "Fix UI button onClick raycast issue", risk_report, "standard"
    )

    assert "unity.ui" in context["rule_cards"]
    assert context["unity_facts"]["ui_system"]["prefab_count"] == 1
    assert (
        "Verify EventSystem, GraphicRaycaster, interactable state, and raycast blockers."
        in context["manual_checks"]
    )


def test_context_pack_selects_graphics_rules_for_texture_task(tmp_path: Path) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)
    UnityProjectScanner(tmp_path, config).scan(deep=True)
    risk_report = RiskClassifier(config).classify(
        "Audit Android iOS texture compression settings", {}
    )

    context = ContextSelector(tmp_path, config).select(
        "Audit Android iOS texture compression settings", risk_report, "standard"
    )

    assert "unity.graphics-platform" in context["rule_cards"]
    assert (
        "Compare Android, iOS, and PC import overrides before recommending changes."
        in context["manual_checks"]
    )


def test_context_pack_selects_execution_path_rule_for_ui_route_task(tmp_path: Path) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)
    UnityProjectScanner(tmp_path, config).scan(deep=True)
    risk_report = RiskClassifier(config).classify(
        "Fix the shop popup button route and controller reset path", {}
    )

    context = ContextSelector(tmp_path, config).select(
        "Fix the shop popup button route and controller reset path",
        risk_report,
        "standard",
    )

    assert "unity.execution-path" in context["rule_cards"]
    assert (
        "Trace the real user path before editing: entry point, open/create call, "
        "prefab or listener binding, controller reset, lock conditions, and final renderer."
        in context["manual_checks"]
    )


def test_context_pack_selects_data_contract_rule_for_payload_task(tmp_path: Path) -> None:
    create_ui_project(tmp_path)
    config = load_config(tmp_path)
    UnityProjectScanner(tmp_path, config).scan(deep=True)
    risk_report = RiskClassifier(config).classify(
        "Verify reward table localization and final packet payload contract", {}
    )

    context = ContextSelector(tmp_path, config).select(
        "Verify reward table localization and final packet payload contract",
        risk_report,
        "standard",
    )

    assert "unity.data-contracts" in context["rule_cards"]
    assert "unity.execution-path" not in context["rule_cards"]
    assert (
        "Verify source table rows, localization keys, displayed text, request/response DTOs, "
        "final payload shape, merge rules, and response apply path."
        in context["manual_checks"]
    )
