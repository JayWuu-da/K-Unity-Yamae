"""Shared constants for K-Unity-Yamae."""

GENERATED_FOLDERS = {"Library", "Temp", "Obj", "Logs", "Builds", "UserSettings", ".vs"}

PROTECTED_YAML_EXTENSIONS = {
    ".unity",
    ".prefab",
    ".asset",
    ".controller",
    ".anim",
    ".overrideController",
    ".playable",
}

RULE_CARD_FILES = {
    "unity.global": "global_rules.md",
    "unity.serialized-field-rename": "serialized_field_rename.md",
    "unity.meta-guid": "meta_guid.md",
    "unity.prefab-scene-yaml": "prefab_scene_yaml.md",
    "unity.asmdef": "asmdef.md",
    "unity.editor-runtime-boundary": "editor_runtime_boundary.md",
    "unity.resources-addressables": "resources_addressables.md",
    "unity.ui": "ui.md",
    "unity.graphics-platform": "graphics_platform.md",
    "unity.architecture-patterns": "architecture_patterns.md",
}

VERIFICATION_TIERS = {
    "0": "Static guards only",
    "1": "Compile/import check",
    "2": "EditMode tests",
    "3": "PlayMode tests",
    "4": "Custom Editor probes",
    "5": "Build validation",
    "M": "Manual Inspector checks required",
}

EDITOR_ONLY_ATTRIBUTES = {
    "MenuItem",
    "ContextMenu",
    "CustomEditor",
    "CustomPropertyDrawer",
    "InitializeOnLoad",
    "DidReloadScripts",
    "PostProcessBuild",
}
