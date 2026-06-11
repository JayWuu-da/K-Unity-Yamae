import json
from pathlib import Path

from click.testing import CliRunner

import kunity_yamae.cli_providers as cli_providers
from kunity_yamae.cli import main


def create_bom_project(project_path: Path) -> None:
    (project_path / "ProjectSettings").mkdir()
    (project_path / "ProjectSettings" / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 6000.4.0f1\n",
        encoding="utf-8",
    )
    (project_path / "Packages").mkdir()
    (project_path / "Packages" / "manifest.json").write_text(
        json.dumps({"dependencies": {"com.unity.ugui": "2.0.0"}}),
        encoding="utf-8-sig",
    )
    (project_path / "Assets" / "UI").mkdir(parents=True)
    (project_path / "Assets" / "UI" / "Shop.prefab").write_text(
        "GameObject:\n  m_Name: Shop\nCanvas:\nGraphicRaycaster:\nm_OnClick:\n",
        encoding="utf-8",
    )


def test_provider_doctor_survives_nested_sdk_module_not_found(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    def raise_for_google(name: str):
        if name == "google.genai":
            raise ModuleNotFoundError("No module named 'google'")
        return object()

    monkeypatch.setattr(cli_providers.importlib.util, "find_spec", raise_for_google)

    doctor = cli_providers.build_provider_doctor({
        "agents": {"backends": {"gemini": {"api_key_env": "GOOGLE_API_KEY"}}}
    })

    assert doctor["providers"]["gemini"]["sdk_available"] is False
    assert doctor["providers"]["gemini"]["problems"] == [
        "missing_credentials",
        "missing_sdk",
    ]
    assert doctor["providers"]["gemini"]["status"] == "missing_credentials"


def test_inspect_accepts_utf8_sig_manifest(tmp_path: Path) -> None:
    create_bom_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "inspect", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.inspect-report.v1"
    assert payload["ui"]["prefab_count"] == 1


def test_context_accepts_utf8_sig_manifest(tmp_path: Path) -> None:
    create_bom_project(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["--project", str(tmp_path), "context", "Fix UI raycast"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.context-pack.v1"
    assert "unity.ui" in payload["rule_cards"]
