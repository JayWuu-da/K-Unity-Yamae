"""Tests for Unity project scanner."""

import json
import tempfile
from pathlib import Path

from kunity_yamae.scanner import UnityProjectScanner


def make_config():
    return {
        "protected_files": {
            "block_direct_write": ["Assets/**/*.meta"],
            "escalate_direct_write": ["Assets/**/*.asmdef"],
            "never_touch": ["Library/**"],
        }
    }


def test_scan_non_unity_project():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        scanner = UnityProjectScanner(project_path, make_config())
        profile = scanner.scan()
        assert profile["unity_version"] == "unknown"
        assert profile["packages"] == {}


def test_scan_unity_project():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        (project_path / "ProjectSettings").mkdir()
        (project_path / "ProjectSettings" / "ProjectVersion.txt").write_text(
            "m_EditorVersion: 6000.4.0f1\nm_EditorVersionWithRevision: 6000.4.0f1 (abc123)"
        )
        (project_path / "Packages").mkdir()
        (project_path / "Packages" / "manifest.json").write_text(
            json.dumps({"dependencies": {"com.unity.test-framework": "1.1.33"}})
        )
        scanner = UnityProjectScanner(project_path, make_config())
        profile = scanner.scan()
        assert profile["unity_version"] == "6000.4.0f1"
        assert "com.unity.test-framework" in profile["packages"]


def test_scan_detects_asmdef():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        (project_path / "ProjectSettings").mkdir()
        (project_path / "ProjectSettings" / "ProjectVersion.txt").write_text(
            "m_EditorVersion: 6000.0.0f1"
        )
        asm_dir = project_path / "Assets" / "Game"
        asm_dir.mkdir(parents=True)
        (asm_dir / "Game.asmdef").write_text(
            json.dumps(
                {
                    "name": "Game.Runtime",
                    "references": [],
                    "includePlatforms": [],
                    "excludePlatforms": [],
                }
            )
        )
        scanner = UnityProjectScanner(project_path, make_config())
        profile = scanner.scan(deep=True)
        assert len(profile["assemblies"]) == 1
        assert profile["assemblies"][0]["name"] == "Game.Runtime"
