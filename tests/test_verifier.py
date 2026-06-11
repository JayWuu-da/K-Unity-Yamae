from pathlib import Path

from kunity_yamae import verifier
from kunity_yamae.verifier import UnityVerifier


def test_custom_method_uses_utf8_replace_for_batchmode_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls = []

    class Completed:
        returncode = 0

    def fake_run(cmd, **kwargs):
        calls.append({"cmd": cmd, "kwargs": kwargs})
        return Completed()

    monkeypatch.setattr(verifier.subprocess, "run", fake_run)

    result = UnityVerifier(tmp_path, {"unity": {"project_path": str(tmp_path)}})._run_custom_method(
        "Unity.exe",
        "KUnityYamae.Editor.HarnessChecks.RunEditorInspection",
    )

    assert result["status"] == "passed"
    assert calls[0]["kwargs"]["encoding"] == "utf-8"
    assert calls[0]["kwargs"]["errors"] == "replace"


def test_custom_method_failure_reports_process_output(tmp_path: Path, monkeypatch) -> None:
    class Completed:
        returncode = 1
        stdout = "fake stdout"
        stderr = "fake stderr"

    monkeypatch.setattr(verifier.subprocess, "run", lambda *_args, **_kwargs: Completed())

    result = UnityVerifier(tmp_path, {"unity": {"project_path": str(tmp_path)}})._run_custom_method(
        "Unity.exe",
        "KUnityYamae.Editor.HarnessChecks.RunEditorInspection",
    )

    assert result["status"] == "failed"
    assert "fake stdout" in result["details"]
    assert "fake stderr" in result["details"]


def test_custom_method_uses_resolved_project_path_when_config_keeps_default_dot(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls = []

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return Completed()

    monkeypatch.setattr(verifier.subprocess, "run", fake_run)

    UnityVerifier(tmp_path, {"unity": {"project_path": "."}})._run_custom_method(
        "Unity.exe",
        "KUnityYamae.Editor.HarnessChecks.RunEditorInspection",
    )

    project_arg = calls[0][calls[0].index("-projectPath") + 1]
    assert project_arg == str(tmp_path)


def test_custom_method_reports_skipped_when_unity_executable_is_missing(tmp_path: Path) -> None:
    result = UnityVerifier(tmp_path, {"unity": {"project_path": "."}})._run_custom_method(
        None,
        "KUnityYamae.Editor.HarnessChecks.RunEditorInspection",
    )

    assert result["status"] == "skipped"
    assert result["details"] == "Unity executable not found"
