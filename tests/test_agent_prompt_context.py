import json
from pathlib import Path

from kunity_yamae.agents.base import BaseAgent
from kunity_yamae.config import load_config
from kunity_yamae.risk import RiskClassifier
from kunity_yamae.scanner import UnityProjectScanner


class PromptOnlyAgent(BaseAgent):
    def execute(self, task, project_path, risk_report, mode, ledger):
        return {}


def create_project(project_path: Path) -> None:
    (project_path / "ProjectSettings").mkdir()
    (project_path / "ProjectSettings" / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 6000.4.0f1\n",
        encoding="utf-8",
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


def test_agent_prompt_includes_unity_facts_and_manual_checks(tmp_path: Path) -> None:
    create_project(tmp_path)
    config = load_config(tmp_path)
    UnityProjectScanner(tmp_path, config).scan(deep=True)
    risk_report = RiskClassifier(config).classify("Fix UI button raycast", {})
    agent = PromptOnlyAgent("prompt-only", config, {})

    prompt = agent._build_prompt("Fix UI button raycast", risk_report, "asset_safe", tmp_path)

    assert "## Unity Facts" in prompt
    assert "ui_system" in prompt
    assert "## Manual Checks" in prompt
    assert "GraphicRaycaster" in prompt
