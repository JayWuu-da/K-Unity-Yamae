from pathlib import Path
from typing import Final

from .constants import GENERATED_FOLDERS

VFX_PATTERNS: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("rain", ("rain", "stormfall", "starfall")),
    ("slash", ("slash", "cleave")),
    ("aura", ("aura", "enchant", "shield")),
    ("orbit", ("orbit", "orbital")),
    ("projectile", ("projectile", "missile", "fireball", "rocket")),
    ("impact", ("hit", "impact", "blast", "explosion")),
    ("beam", ("beam", "laser", "line")),
    ("wall", ("wall", "barrier")),
    ("pickup", ("loot", "pickup", "drop")),
)

RUNTIME_TASK_TOKENS: Final[tuple[str, ...]] = (
    "vfx",
    "visual",
    "ability",
    "spawn",
    "instantiate",
    "resources.load",
    "resources",
    "recursion",
    "recursive",
    "clone",
    "collider",
)


def detect_vfx_semantics(project_path: Path) -> dict:
    items: list[dict[str, str]] = []
    summary: dict[str, int] = {category: 0 for category, _ in VFX_PATTERNS}
    for prefab in _iter_project_files(project_path, "*.prefab"):
        category = _classify_prefab(prefab)
        if category is None:
            continue
        relative = _relative(project_path, prefab)
        items.append({"path": relative, "category": category})
        summary[category] += 1
    return {
        "summary": {key: value for key, value in summary.items() if value > 0},
        "prefabs": items[:40],
        "recommendation": (
            "Map gameplay abilities to semantic VFX buckets before hand-picking prefabs."
        ),
    }


def runtime_safety_hints(task: str, project_path: Path) -> dict:
    task_lower = task.lower()
    if not any(token in task_lower for token in RUNTIME_TASK_TOKENS):
        return {}

    checks = {
        "cap_spawn_counts",
        "destroy_transient_vfx",
        "guard_recursive_ability_events",
        "remove_or_disable_vfx_colliders",
        "verify_resources_load_paths",
    }
    scripts = _find_runtime_sensitive_scripts(project_path)
    return {
        "checks": sorted(checks),
        "scripts": scripts[:25],
        "notes": [
            "VFX spawned at runtime should have explicit lifetime or pooling.",
            "Child ability events should suppress their parent trigger to prevent recursion.",
            "Procedural VFX primitives should remove colliders unless gameplay "
            "collision is intended.",
            "Resources.Load paths should be covered by scan/context evidence or runtime fallback.",
        ],
    }


def _classify_prefab(path: Path) -> str | None:
    haystack = path.as_posix().lower()
    for category, tokens in VFX_PATTERNS:
        if any(token in haystack for token in tokens):
            return category
    return None


def _find_runtime_sensitive_scripts(project_path: Path) -> list[str]:
    scripts: list[str] = []
    needles = (
        "Resources.Load",
        "Instantiate(",
        "GameObject.CreatePrimitive",
        "Destroy(",
        "AbilityEvent",
        "Trigger(",
        "Collider",
    )
    for script in _iter_project_files(project_path, "*.cs"):
        content = script.read_text(encoding="utf-8", errors="replace")
        if any(needle in content for needle in needles):
            scripts.append(_relative(project_path, script))
    return scripts


def _iter_project_files(project_path: Path, pattern: str) -> list[Path]:
    paths: list[Path] = []
    for path in project_path.rglob(pattern):
        try:
            relative_parts = path.relative_to(project_path).parts
        except ValueError:
            continue
        if GENERATED_FOLDERS & set(relative_parts):
            continue
        paths.append(path)
    return paths


def _relative(project_path: Path, path: Path) -> str:
    return str(path.relative_to(project_path)).replace("\\", "/")
