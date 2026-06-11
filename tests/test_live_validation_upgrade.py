import json
from pathlib import Path

from click.testing import CliRunner

from kunity_yamae.cli import main
from kunity_yamae.config import load_config
from kunity_yamae.context import ContextSelector
from kunity_yamae.risk import RiskClassifier
from kunity_yamae.scanner import UnityProjectScanner
from tests.fixtures.make_unity_project import create_minimal_project


def test_scan_reports_runtime_asmdefs_and_vfx_semantics(tmp_path: Path) -> None:
    create_live_validation_project(tmp_path)

    profile = UnityProjectScanner(tmp_path, load_config(tmp_path)).scan()

    assert any(item["name"] == "Sample.Runtime" for item in profile["assemblies"])
    assert profile["vfx_semantics"]["summary"]["rain"] == 1
    assert profile["vfx_semantics"]["summary"]["slash"] == 1
    assert profile["vfx_semantics"]["summary"]["aura"] == 1
    assert profile["vfx_semantics"]["summary"]["orbit"] == 1


def test_verify_plan_includes_live_visual_and_test_assembly_guidance(tmp_path: Path) -> None:
    create_live_validation_project(tmp_path)
    UnityProjectScanner(tmp_path, load_config(tmp_path)).scan()
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--project",
            str(tmp_path),
            "verify",
            "--dry-run",
            "--json",
            "--qa-level",
            "minimal",
            "--live",
            "--visual-smoke",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["qa_level"] == "minimal"
    assert payload["unity_mcp"]["recommended"] is True
    assert "manage_editor.play" in payload["unity_mcp"]["scenario"][2]
    assert any("manage_scene.get_hierarchy" in step for step in payload["unity_mcp"]["scenario"])
    assert payload["test_assembly_suggestions"] == ["SampleEditModeTests"]
    assert payload["visual_smoke"]["screenshot_name"] == "visual-smoke.png"


def test_context_pack_surfaces_runtime_safety_hints(tmp_path: Path) -> None:
    create_live_validation_project(tmp_path)
    config = load_config(tmp_path)
    profile = UnityProjectScanner(tmp_path, config).scan()
    risk_report = RiskClassifier(config).classify(
        "Add VFX ability Resources.Load recursion spawn collider visual smoke",
        profile,
    )

    context = ContextSelector(tmp_path, config).select(
        "Add VFX ability Resources.Load recursion spawn collider visual smoke",
        risk_report,
        "standard",
    )

    assert "runtime_safety" in context["unity_facts"]
    assert "cap_spawn_counts" in context["unity_facts"]["runtime_safety"]["checks"]
    assert "destroy_transient_vfx" in context["unity_facts"]["runtime_safety"]["checks"]
    assert "guard_recursive_ability_events" in context["unity_facts"]["runtime_safety"]["checks"]
    assert "Resources.Load" in " ".join(context["manual_checks"])


def test_korean_readme_documents_unity_mcp_workflow() -> None:
    readme = Path("README_KO.md")

    assert readme.exists()
    content = readme.read_text(encoding="utf-8")
    assert "Unity MCP" in content
    assert "https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main" in content
    assert "verify --dry-run --json --qa-level minimal --live --visual-smoke" in content
    assert "시각 스모크" in content


def create_live_validation_project(project_path: Path) -> None:
    create_minimal_project(project_path)
    (project_path / "Packages" / "manifest.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "com.unity.test-framework": "1.6.0",
                    "com.coplaydev.unity-mcp": "https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main",
                }
            }
        ),
        encoding="utf-8",
    )
    (project_path / "Assets" / "Scripts" / "Runtime").mkdir(parents=True)
    (project_path / "Assets" / "Tests" / "EditMode").mkdir(parents=True)
    (project_path / "Assets" / "Resources" / "AbilityVFX").mkdir(parents=True)
    runtime_asmdef = project_path / "Assets" / "Scripts" / "Runtime" / "Sample.Runtime.asmdef"
    runtime_asmdef.write_text(
        json.dumps(
            {
                "name": "Sample.Runtime",
                "references": [],
                "includePlatforms": [],
            }
        ),
        encoding="utf-8",
    )
    (
        project_path
        / "Assets"
        / "Tests"
        / "EditMode"
        / "SampleEditModeTests.asmdef"
    ).write_text(
        json.dumps({"name": "SampleEditModeTests", "includePlatforms": ["Editor"]}),
        encoding="utf-8",
    )
    for prefab_name in (
        "FireRain.prefab",
        "FireSlash.prefab",
        "FireAura.prefab",
        "FireOrbit.prefab",
        "VoidHit.prefab",
    ):
        prefab = project_path / "Assets" / "Resources" / "AbilityVFX" / prefab_name
        prefab.write_text(
            "PrefabInstance:\nParticleSystem:\n",
            encoding="utf-8",
        )
    (project_path / "Assets" / "Scripts" / "Runtime" / "AbilityLoadout.cs").write_text(
        "\n".join(
            [
                "using UnityEngine;",
                "public sealed class AbilityLoadout : MonoBehaviour",
                "{",
                "    private GameObject prefab;",
                "    private void Spawn()",
                "    {",
                "        Resources.Load<GameObject>(\"AbilityVFX/FireRain\");",
                "        GameObject.CreatePrimitive(PrimitiveType.Sphere);",
                "    }",
                "}",
            ]
        ),
        encoding="utf-8",
    )
