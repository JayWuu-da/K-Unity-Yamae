import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("skills/unity-data-validator-builder/scripts/scaffold_validator.py")


def run_scaffold(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        check=False,
        encoding="utf-8",
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def create_shop_pass_tables(project_path: Path) -> None:
    table_root = project_path / "Assets" / "Resources" / "TableDatas"
    write_json(
        table_root / "Shop.json",
        {
            "Pass": [
                {
                    "ID": "1",
                    "PRODUCT_ID": "100",
                    "PRODUCT_GROUP_ID": "10",
                    "LEVEL_COUNT": "2",
                    "NAME_KEY": "text_pass_name",
                },
                {
                    "ID": "2",
                    "PRODUCT_ID": "101",
                    "PRODUCT_GROUP_ID": "10",
                    "LEVEL_COUNT": "2",
                    "NAME_KEY": "text_pass_name",
                },
            ],
            "Product": [
                {"ID": "100", "TYPE": "10", "PURCHASE_ID": "pass_product_100"},
            ],
            "PassProduct": [
                {"ID": "1", "GROUP_ID": "10", "LEVEL": "1", "TYPE": "0", "REWARD_ID": "500"},
                {"ID": "2", "GROUP_ID": "10", "LEVEL": "1", "TYPE": "1", "REWARD_ID": "501"},
            ],
        },
    )
    write_json(
        table_root / "Package.json",
        {
            "Package": [
                {"ID": "100", "product_id": "sku-pass-100", "PurchaseType": "Pass"},
                {"ID": "101", "product_id": "sku-pass-101", "PurchaseType": "Pass"},
                {"ID": "200", "product_id": None, "PurchaseType": "Limited"},
            ]
        },
    )
    write_json(
        table_root / "Reward.json",
        {
            "Reward": [
                {"ID": "1", "REWARD_ID": "500", "TYPE": "1", "VALUE": "10", "COUNT": "1"},
                {"ID": "2", "REWARD_ID": "501", "TYPE": "2", "VALUE": "20", "COUNT": "1"},
            ]
        },
    )
    write_json(
        table_root / "LocalizeText.json",
        {"Shop": [{"ID": "1", "TEXT": "text_pass_name", "KR": "패스", "EN": "Pass"}]},
    )


def run_generated_validator(
    output_path: Path,
    project_path: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(output_path / "src" / "validator.py"),
            "--project",
            str(project_path),
            "--profile",
            str(output_path / "profiles" / "shop-pass.yaml"),
            "--report-md",
            str(output_path / "reports" / "shop-pass.md"),
            "--report-json",
            str(output_path / "reports" / "shop-pass.json"),
        ],
        check=False,
        encoding="utf-8",
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )


def test_scaffold_creates_generic_validator_project_and_validates_shop_pass_tables(
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "UnityProject"
    output_path = tmp_path / "GeneratedValidator"
    create_shop_pass_tables(project_path)

    scaffold = run_scaffold(
        "--project",
        str(project_path),
        "--domain",
        "shop-pass",
        "--output",
        str(output_path),
    )

    assert scaffold.returncode == 0, scaffold.stderr
    assert (output_path / "README.md").exists()
    assert (output_path / "profiles" / "shop-pass.yaml").exists()
    assert (output_path / "src" / "validator.py").exists()
    assert (output_path / "tests" / "test_validator_contract.py").exists()
    assert (output_path / "reports" / ".gitkeep").exists()

    result = run_generated_validator(output_path, project_path)

    assert result.returncode == 0, result.stderr
    report = json.loads((output_path / "reports" / "shop-pass.json").read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["summary"]["checked_tables"] == 6
    assert report["summary"]["checked_relationships"] >= 4


def test_scaffold_rejects_unsafe_domain_name(tmp_path: Path) -> None:
    result = run_scaffold(
        "--project",
        str(tmp_path / "UnityProject"),
        "--domain",
        "../bad",
        "--output",
        str(tmp_path / "GeneratedValidator"),
    )

    assert result.returncode != 0
    assert "domain" in result.stderr
    assert "safe" in result.stderr
    assert not (tmp_path / "GeneratedValidator").exists()


def test_scaffold_refuses_existing_output_without_force(tmp_path: Path) -> None:
    output_path = tmp_path / "GeneratedValidator"
    output_path.mkdir()
    marker = output_path / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    result = run_scaffold(
        "--project",
        str(tmp_path / "UnityProject"),
        "--domain",
        "shop-pass",
        "--output",
        str(output_path),
    )

    assert result.returncode != 0
    assert "--force" in result.stderr
    assert marker.read_text(encoding="utf-8") == "keep"


def test_scaffold_force_refuses_project_root_output(tmp_path: Path) -> None:
    project_path = tmp_path / "UnityProject"
    marker = project_path / "ProjectSettings" / "ProjectVersion.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("m_EditorVersion: 6000.0.0f1", encoding="utf-8")

    result = run_scaffold(
        "--project",
        str(project_path),
        "--domain",
        "shop-pass",
        "--output",
        str(project_path),
        "--force",
    )

    assert result.returncode != 0
    assert "output" in result.stderr
    assert marker.read_text(encoding="utf-8") == "m_EditorVersion: 6000.0.0f1"


def test_scaffold_force_refuses_project_child_output(tmp_path: Path) -> None:
    project_path = tmp_path / "UnityProject"
    output_path = project_path / "Assets" / "GeneratedValidator"
    marker = output_path / "keep.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("keep", encoding="utf-8")

    result = run_scaffold(
        "--project",
        str(project_path),
        "--domain",
        "shop-pass",
        "--output",
        str(output_path),
        "--force",
    )

    assert result.returncode != 0
    assert "output" in result.stderr
    assert marker.read_text(encoding="utf-8") == "keep"
    assert not (output_path / "src" / "validator.py").exists()


def test_generated_validator_reports_missing_relationship(tmp_path: Path) -> None:
    project_path = tmp_path / "UnityProject"
    output_path = tmp_path / "GeneratedValidator"
    create_shop_pass_tables(project_path)
    shop_path = project_path / "Assets" / "Resources" / "TableDatas" / "Shop.json"
    shop = json.loads(shop_path.read_text(encoding="utf-8"))
    shop["Pass"][0]["PRODUCT_ID"] = "999"
    shop_path.write_text(json.dumps(shop), encoding="utf-8")
    scaffold = run_scaffold(
        "--project",
        str(project_path),
        "--domain",
        "shop-pass",
        "--output",
        str(output_path),
    )
    assert scaffold.returncode == 0, scaffold.stderr

    result = run_generated_validator(output_path, project_path)

    assert result.returncode != 0
    report = json.loads((output_path / "reports" / "shop-pass.json").read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert any("PRODUCT_ID" in issue["message"] for issue in report["issues"])


def test_skill_files_do_not_contain_project_specific_examples() -> None:
    skill_root = Path("skills/unity-data-validator-builder")
    if not skill_root.exists():
        return
    banned_patterns = ["D:/", "C:/", "profiles/project-", "project-specific-example"]
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in skill_root.rglob("*")
        if path.is_file() and path.suffix in {".md", ".py", ".yaml"}
    )

    found = [pattern for pattern in banned_patterns if pattern in text]

    assert found == []
