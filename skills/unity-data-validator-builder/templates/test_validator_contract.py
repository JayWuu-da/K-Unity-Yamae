from pathlib import Path


def test_profile_exists() -> None:
    assert Path("profiles").exists()
