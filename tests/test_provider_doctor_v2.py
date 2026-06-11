import json
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main


def create_minimal_project(project_path: Path) -> None:
    (project_path / "ProjectSettings").mkdir()
    (project_path / "ProjectSettings" / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 6000.4.0f1\n",
        encoding="utf-8",
    )
    (project_path / "Packages").mkdir()
    (project_path / "Packages" / "manifest.json").write_text(
        json.dumps({"dependencies": {}}),
        encoding="utf-8",
    )
    (project_path / "Assets").mkdir()


def test_provider_doctor_v2_reports_missing_openai_key_without_traceback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    create_minimal_project(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "providers",
            "doctor",
            "codex",
            "--json",
        ],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "unity-harness.provider-doctor.v2"
    assert payload["providers"]["codex"]["status"] == "missing_credentials"
    assert "traceback" not in result.output.lower()


def test_provider_doctor_v2_accepts_fake_provider_endpoint(
    tmp_path: Path,
    monkeypatch,
) -> None:
    create_minimal_project(tmp_path)
    monkeypatch.setenv("KUNITY_FAKE_OPENAI_KEY", "test-key")
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "providers",
            "doctor",
            "codex",
            "--endpoint",
            "http://127.0.0.1:8787/v1/responses",
            "--api-key-env",
            "KUNITY_FAKE_OPENAI_KEY",
            "--no-live",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    provider = payload["providers"]["codex"]
    assert provider["status"] in {"ready", "missing_sdk"}
    assert provider["endpoint"] == "http://127.0.0.1:8787/v1/responses"
    assert provider["live_checked"] is False
