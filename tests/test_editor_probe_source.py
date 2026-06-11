from pathlib import Path


def test_editor_probe_uses_unity_event_persistent_listener_api() -> None:
    source = Path("Editor/EditorInspectionProbe.cs").read_text(encoding="utf-8")

    assert "UnityEventBase" in source
    assert "GetPersistentEventCount" in source
    assert "GetPersistentTarget" in source
    assert "GetPersistentMethodName" in source
    assert "m_PersistentCalls.m_Calls" not in source
