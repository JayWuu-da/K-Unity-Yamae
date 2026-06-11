"""Tests for risk classifier."""

from kunity_yamae.risk import RiskClassifier


def make_config():
    return {
        "risk": {"low_max": 29, "standard_max": 59, "asset_safe_max": 79, "migration_min": 80},
        "file_risk_scores": {},
        "protected_files": {
            "block_direct_write": ["Assets/**/*.meta", "Assets/**/*.unity"],
            "escalate_direct_write": ["Assets/**/*.asmdef"],
            "never_touch": ["Library/**"],
        },
    }


def make_profile():
    return {"packages": {}, "assemblies": [], "scenes": []}


def test_low_risk_fix():
    config = make_config()
    classifier = RiskClassifier(config)
    report = classifier.classify("Fix null check in DamageCalculator", make_profile())
    assert report["risk_score"] < 30
    assert report["mode"] == "fast_patch"


def test_medium_risk_monobehaviour():
    config = make_config()
    classifier = RiskClassifier(config)
    report = classifier.classify("Make EnemySpawner wait before spawning", make_profile())
    assert 30 <= report["risk_score"] <= 59
    assert report["mode"] == "standard"


def test_high_risk_rename():
    config = make_config()
    classifier = RiskClassifier(config)
    report = classifier.classify("Rename PlayerStats.hitpoints to health", make_profile())
    assert report["risk_score"] >= 80
    assert report["mode"] == "migration"
    assert any("Serialized" in t for t in report["triggers"])


def test_asset_move_risk():
    config = make_config()
    classifier = RiskClassifier(config)
    report = classifier.classify("Move all UI prefabs to Assets/UI/Prefabs", make_profile())
    assert report["risk_score"] >= 60


def test_editor_script_risk():
    config = make_config()
    classifier = RiskClassifier(config)
    report = classifier.classify("Add a custom inspector for QuestData", make_profile())
    assert any("Editor" in t for t in report["triggers"])


def test_asmdef_risk():
    config = make_config()
    classifier = RiskClassifier(config)
    report = classifier.classify("Change asmdef references for Game.Core", make_profile())
    assert report["risk_score"] >= 60
    assert any("asmdef" in t.lower() for t in report["triggers"])


def test_risk_report_has_required_fields():
    config = make_config()
    classifier = RiskClassifier(config)
    report = classifier.classify("Fix typo in comments", make_profile())
    assert "schema" in report
    assert "task" in report
    assert "risk_score" in report
    assert "mode" in report
    assert "triggers" in report
    assert "required_rule_cards" in report
    assert "blocked_operations" in report
    assert "required_verification" in report
    assert "rationale" in report
