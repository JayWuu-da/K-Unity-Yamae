import subprocess
import sys
from pathlib import Path


def test_make_unity_project_creates_ui_graphics_architecture_fixture(
    tmp_path: Path,
) -> None:
    target = tmp_path / "project"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tests.fixtures.make_unity_project",
            "--kind",
            "ui-graphics-architecture",
            "--out",
            str(target),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert (target / "ProjectSettings" / "ProjectVersion.txt").exists()
    assert (target / "Assets" / "UI" / "MainMenu.prefab").exists()
    assert (target / "Assets" / "Textures" / "Hero.png.meta").exists()
    assert (target / "Assets" / "Scripts" / "ShopPresenter.cs").exists()
    assert "FIXTURE_OK" in result.stdout


def test_make_unity_project_rejects_unknown_kind(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tests.fixtures.make_unity_project",
            "--kind",
            "unknown",
            "--out",
            str(tmp_path / "bad"),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode != 0
    assert "unknown fixture kind" in result.stderr
