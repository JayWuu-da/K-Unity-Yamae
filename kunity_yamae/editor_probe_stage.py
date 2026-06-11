from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from shutil import copy2, rmtree

PROBE_FILES = ("HarnessChecks.cs", "EditorInspectionProbe.cs", "EditorInspectionJson.cs")


@contextmanager
def stage_editor_probe(project_path: Path) -> Iterator[Path]:
    source_root = Path(__file__).resolve().parent.parent / "Editor"
    editor_root = project_path / "Assets" / "Editor"
    target_root = project_path / "Assets" / "Editor" / "KUnityYamaeHarness"
    editor_root_existed = editor_root.exists()
    target_root_existed = target_root.exists()
    created_files: list[Path] = []
    target_root.mkdir(parents=True, exist_ok=True)
    try:
        for filename in PROBE_FILES:
            source = source_root / filename
            target = target_root / filename
            if not target.exists():
                copy2(source, target)
                created_files.append(target)
        yield target_root
    finally:
        for path in created_files:
            if path.exists():
                path.unlink()
            meta_path = path.with_name(f"{path.name}.meta")
            if meta_path.exists():
                meta_path.unlink()
        if target_root.exists() and not any(target_root.iterdir()):
            rmtree(target_root)
        if not target_root_existed:
            target_meta = target_root.with_name(f"{target_root.name}.meta")
            if target_meta.exists():
                target_meta.unlink()
        if editor_root.exists() and not any(editor_root.iterdir()) and not editor_root_existed:
            rmtree(editor_root)
        if not editor_root_existed:
            editor_meta = editor_root.with_name(f"{editor_root.name}.meta")
            if editor_meta.exists():
                editor_meta.unlink()
