import json
import re
from pathlib import Path
from typing import Final

from .constants import GENERATED_FOLDERS

RENDER_PIPELINE_PACKAGES: Final[dict[str, str]] = {
    "com.unity.render-pipelines.universal": "urp",
    "com.unity.render-pipelines.high-definition": "hdrp",
}


def collect_unity_facts(project_path: Path, packages: dict[str, str]) -> dict:
    return {
        "render_pipeline": _detect_render_pipeline(project_path, packages),
        "input_system": _detect_input_system(project_path, packages),
        "platform_targets": _detect_platform_targets(project_path),
        "asset_summary": _detect_asset_summary(project_path),
        "ui_system": _detect_ui_system(project_path),
        "graphics_defaults": _detect_graphics_defaults(project_path),
        "architecture_patterns": _detect_architecture_patterns(project_path),
    }


def load_cached_profile(project_path: Path) -> dict:
    profile_path = project_path / ".unity-harness" / "cache" / "project-profile.json"
    fallback_path = project_path / ".unity-harness" / "project-profile.json"
    for path in (profile_path, fallback_path):
        if path.exists():
            with open(path, "r", encoding="utf-8") as file:
                loaded = json.load(file)
            if isinstance(loaded, dict):
                return loaded
    return {}


def _detect_render_pipeline(project_path: Path, packages: dict[str, str]) -> str:
    for package_name, pipeline in RENDER_PIPELINE_PACKAGES.items():
        if package_name in packages:
            return pipeline
    graphics_settings = project_path / "ProjectSettings" / "GraphicsSettings.asset"
    if not graphics_settings.exists():
        return "builtin"
    content = graphics_settings.read_text(encoding="utf-8", errors="replace")
    if "m_RenderPipelineAsset: {fileID: 0}" in content:
        return "builtin"
    if "m_RenderPipelineAsset:" in content:
        return "srp"
    return "builtin"


def _detect_input_system(project_path: Path, packages: dict[str, str]) -> str:
    has_new_input = "com.unity.inputsystem" in packages
    settings = project_path / "ProjectSettings" / "ProjectSettings.asset"
    content = settings.read_text(encoding="utf-8", errors="replace") if settings.exists() else ""
    if "activeInputHandler: 2" in content:
        return "both"
    if "activeInputHandler: 1" in content:
        return "new" if has_new_input else "old"
    if "activeInputHandler: 0" in content:
        return "old"
    return "new" if has_new_input else "unknown"


def _detect_platform_targets(project_path: Path) -> list[str]:
    targets: set[str] = set()
    for meta_path in _iter_project_files(project_path, "*.meta"):
        content = meta_path.read_text(encoding="utf-8", errors="replace")
        targets.update(re.findall(r"buildTarget:\s*([A-Za-z0-9_]+)", content))
    return sorted(targets)


def _detect_asset_summary(project_path: Path) -> dict:
    prefabs = list(_iter_project_files(project_path, "*.prefab"))
    scenes = list(_iter_project_files(project_path, "*.unity"))
    scriptable_assets = list(_iter_project_files(project_path, "*.asset"))
    return {
        "prefab_count": len(prefabs),
        "scene_count": len(scenes),
        "asset_count": len(scriptable_assets),
        "prefabs": [_relative(project_path, path) for path in prefabs[:25]],
        "scenes": [_relative(project_path, path) for path in scenes[:25]],
    }


def _detect_ui_system(project_path: Path) -> dict:
    prefab_count = 0
    button_like_count = 0
    event_system_count = 0
    graphic_raycaster_count = 0
    canvas_group_count = 0
    missing_script_count = 0
    ui_paths: list[str] = []
    prefab_wiring: list[dict] = []
    for path in [
        *_iter_project_files(project_path, "*.prefab"),
        *_iter_project_files(project_path, "*.unity"),
    ]:
        content = path.read_text(encoding="utf-8", errors="replace")
        has_ui = any(
            token in content
            for token in ("Canvas", "GraphicRaycaster", "CanvasGroup", "m_OnClick")
        )
        if not has_ui:
            continue
        if path.suffix == ".prefab":
            prefab_count += 1
            prefab_wiring.append(
                {
                    "path": _relative(project_path, path),
                    "button_like_count": content.count("m_OnClick"),
                    "graphic_raycaster_count": content.count("GraphicRaycaster"),
                    "canvas_group_count": content.count("CanvasGroup"),
                    "has_missing_script": bool(_has_missing_script(content)),
                }
            )
        button_like_count += content.count("m_OnClick")
        event_system_count += content.count("EventSystem")
        graphic_raycaster_count += content.count("GraphicRaycaster")
        canvas_group_count += content.count("CanvasGroup")
        if _has_missing_script(content):
            missing_script_count += 1
        ui_paths.append(_relative(project_path, path))
    hierarchy_warnings = []
    if button_like_count > 0 and event_system_count == 0:
        hierarchy_warnings.append("missing_event_system")
    if button_like_count > 0 and graphic_raycaster_count == 0:
        hierarchy_warnings.append("missing_graphic_raycaster")
    return {
        "prefab_count": prefab_count,
        "button_like_count": button_like_count,
        "event_system_count": event_system_count,
        "graphic_raycaster_count": graphic_raycaster_count,
        "canvas_group_count": canvas_group_count,
        "missing_script_count": missing_script_count,
        "prefab_wiring": prefab_wiring[:25],
        "hierarchy_warnings": hierarchy_warnings,
        "paths": ui_paths[:25],
    }


def _detect_graphics_defaults(project_path: Path) -> dict:
    texture_meta_count = 0
    platform_overrides: dict[str, int] = {}
    large_textures: list[str] = []
    texture_import_settings: list[dict] = []
    sprite_import_settings: list[dict] = []
    audio_import_settings: list[dict] = []
    model_import_settings: list[dict] = []
    mobile_pc_mismatches: list[dict] = []
    for path in _iter_project_files(project_path, "*.meta"):
        content = path.read_text(encoding="utf-8", errors="replace")
        if "TextureImporter:" in content:
            texture_meta_count += 1
            for target in re.findall(r"buildTarget:\s*([A-Za-z0-9_]+)", content):
                platform_overrides[target] = platform_overrides.get(target, 0) + 1
            size_match = re.search(r"maxTextureSize:\s*(\d+)", content)
            if size_match and int(size_match.group(1)) >= 4096:
                large_textures.append(_relative(project_path, path))
            setting = _parse_texture_import_settings(project_path, path, content)
            texture_import_settings.append(setting)
            sprite_setting = _parse_sprite_import_settings(project_path, path, content)
            if sprite_setting:
                sprite_import_settings.append(sprite_setting)
            mismatch = _mobile_pc_mismatch(setting)
            if mismatch:
                mobile_pc_mismatches.append(mismatch)
        if "AudioImporter:" in content:
            audio_import_settings.append(_parse_audio_import_settings(project_path, path, content))
        if "ModelImporter:" in content:
            model_import_settings.append(_parse_model_import_settings(project_path, path, content))
    return {
        "texture_meta_count": texture_meta_count,
        "platform_overrides": platform_overrides,
        "large_textures": large_textures[:25],
        "texture_import_settings": texture_import_settings[:25],
        "sprite_import_settings": sprite_import_settings[:25],
        "audio_import_settings": audio_import_settings[:25],
        "model_import_settings": model_import_settings[:25],
        "mobile_pc_mismatches": mobile_pc_mismatches[:25],
    }


def _detect_architecture_patterns(project_path: Path) -> dict:
    presenters = []
    views = []
    controllers = []
    managers = []
    services = []
    event_buses = []
    scriptable_objects = []
    for path in _iter_project_files(project_path, "*.cs"):
        content = path.read_text(encoding="utf-8", errors="replace")
        relative = _relative(project_path, path)
        stem = path.stem.lower()
        if "presenter" in stem:
            presenters.append(relative)
        if stem.endswith("view") or "view" in stem:
            views.append(relative)
        if "controller" in stem:
            controllers.append(relative)
        if "manager" in stem:
            managers.append(relative)
        if "service" in stem:
            services.append(relative)
        if "eventbus" in stem or "event bus" in content.lower():
            event_buses.append(relative)
        if "ScriptableObject" in content:
            scriptable_objects.append(relative)
    detected = []
    if presenters and (views or controllers):
        detected.append("mvp")
    if controllers and views:
        detected.append("mvc")
    if managers:
        detected.append("manager")
    if services:
        detected.append("service")
    confidence = "low"
    if presenters and controllers:
        confidence = "high"
    elif presenters or controllers or managers or services:
        confidence = "medium"
    warnings = []
    if confidence != "high":
        warnings.append("Do not assume architecture ownership from names alone.")
    return {
        "detected": detected,
        "presenters": presenters[:25],
        "views": views[:25],
        "controllers": controllers[:25],
        "managers": managers[:25],
        "services": services[:25],
        "event_buses": event_buses[:25],
        "scriptable_objects": scriptable_objects[:25],
        "confidence": confidence,
        "warnings": warnings,
    }


def _iter_project_files(project_path: Path, pattern: str) -> list[Path]:
    paths = []
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


def _has_missing_script(content: str) -> bool:
    return bool(re.search(r"m_Script:\s*\{[^}]*guid:\s*0{32}", content))


def _parse_texture_import_settings(project_path: Path, path: Path, content: str) -> dict:
    platforms: dict[str, dict] = {}
    current_target = ""
    for raw_line in content.splitlines():
        line = raw_line.strip()
        target_match = re.match(r"-?\s*buildTarget:\s*([A-Za-z0-9_]+)", line)
        if target_match:
            current_target = target_match.group(1)
            platforms[current_target] = {}
            continue
        if not current_target or ":" not in line:
            continue
        key, raw_value = [part.strip() for part in line.split(":", 1)]
        normalized_key = _texture_key(key)
        platforms[current_target][normalized_key] = _parse_texture_value(raw_value)
    return {
        "path": _relative(project_path, path),
        "platforms": platforms,
    }


def _parse_sprite_import_settings(project_path: Path, path: Path, content: str) -> dict | None:
    values = _parse_root_importer_values(
        content,
        {
            "spriteMode": "sprite_mode",
            "spritePixelsToUnits": "pixels_per_unit",
            "mipmapEnabled": "mipmap_enabled",
            "isReadable": "is_readable",
        },
    )
    sprite_mode = values.get("sprite_mode")
    if sprite_mode in {None, 0, "0"}:
        return None
    values["sprite_mode"] = _sprite_mode_name(sprite_mode)
    return {
        "path": _relative(project_path, path),
        **values,
    }


def _parse_audio_import_settings(project_path: Path, path: Path, content: str) -> dict:
    return {
        "path": _relative(project_path, path),
        **_parse_root_importer_values(
            content,
            {
                "loadType": "load_type",
                "compressionFormat": "compression_format",
                "quality": "quality",
                "preloadAudioData": "preload_audio_data",
            },
        ),
    }


def _parse_model_import_settings(project_path: Path, path: Path, content: str) -> dict:
    return {
        "path": _relative(project_path, path),
        **_parse_root_importer_values(
            content,
            {
                "meshCompression": "mesh_compression",
                "isReadable": "is_readable",
                "optimizeMeshPolygons": "optimize_mesh_polygons",
                "importBlendShapes": "import_blend_shapes",
            },
        ),
    }


def _parse_root_importer_values(content: str, key_map: dict[str, str]) -> dict:
    values = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line.startswith("- ") or ":" not in line:
            continue
        key, raw_value = [part.strip() for part in line.split(":", 1)]
        if key in key_map:
            values[key_map[key]] = _parse_texture_value(raw_value)
    return values


def _texture_key(key: str) -> str:
    mapping = {
        "maxTextureSize": "max_texture_size",
        "textureCompression": "texture_compression",
        "compressionQuality": "compression_quality",
        "crunchedCompression": "crunched_compression",
    }
    return mapping.get(key, key)


def _parse_texture_value(value: str) -> int | str:
    if re.fullmatch(r"\d+\.\d+", value):
        return float(value)
    if re.fullmatch(r"\d+", value):
        return int(value)
    return value


def _sprite_mode_name(value: int | str) -> str:
    mapping = {
        1: "Single",
        2: "Multiple",
        3: "Polygon",
        "1": "Single",
        "2": "Multiple",
        "3": "Polygon",
    }
    return mapping.get(value, str(value))


def _mobile_pc_mismatch(setting: dict) -> dict | None:
    platforms = setting.get("platforms", {})
    android = platforms.get("Android", {})
    iphone = platforms.get("iPhone", {})
    standalone = platforms.get("Standalone", {})
    mobile_formats = {android.get("format"), iphone.get("format")} - {None, ""}
    standalone_format = standalone.get("format")
    if standalone_format and mobile_formats and standalone_format not in mobile_formats:
        return {
            "path": setting["path"],
            "reason": "mobile_pc_format_mismatch",
            "mobile_formats": sorted(str(item) for item in mobile_formats),
            "standalone_format": standalone_format,
        }
    return None
