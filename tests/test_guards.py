"""Tests for serialization guard."""

from kunity_yamae.guards.serialization_guard import SerializationGuard


def make_guard():
    from pathlib import Path

    return SerializationGuard(
        Path("."), {"serialization": {"require_formerly_serialized_as": True}}
    )


def test_no_rename_no_issues():
    guard = make_guard()
    old = "public class Foo : MonoBehaviour { public int health = 10; }"
    new = "public class Foo : MonoBehaviour { public int health = 10; }"
    issues = guard.check(old, new, "Foo.cs")
    assert len(issues) == 0


def test_rename_without_migration():
    guard = make_guard()
    old = "public class Foo : MonoBehaviour { public int hitpoints = 10; }"
    new = "public class Foo : MonoBehaviour { public int health = 10; }"
    issues = guard.check(old, new, "Foo.cs")
    assert len(issues) >= 1
    assert issues[0]["severity"] == "hard_failure"
    assert "FormerlySerializedAs" in issues[0]["message"]


def test_rename_with_migration():
    guard = make_guard()
    old = "public class Foo : MonoBehaviour { public int hitpoints = 10; }"
    new = """using UnityEngine.Serialization;
public class Foo : MonoBehaviour {
    [FormerlySerializedAs("hitpoints")]
    public int health = 10;
}"""
    issues = guard.check(old, new, "Foo.cs")
    hard_failures = [i for i in issues if i["severity"] == "hard_failure"]
    assert len(hard_failures) == 0


def test_serialize_field_rename():
    guard = make_guard()
    old = "public class Bar : MonoBehaviour { [SerializeField] private string playerName; }"
    new = "public class Bar : MonoBehaviour { [SerializeField] private string characterName; }"
    issues = guard.check(old, new, "Bar.cs")
    assert len(issues) >= 1
    assert issues[0]["severity"] == "hard_failure"
