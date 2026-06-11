"""Unity project scanner - detects project structure and caches facts."""

import json
from datetime import datetime, timezone
from pathlib import Path

from .semantic_index import detect_vfx_semantics
from .unity_profile import collect_unity_facts


class UnityProjectScanner:
    def __init__(self, project_path: Path, config: dict):
        self.project_path = project_path
        self.config = config
        self.cache_dir = project_path / ".unity-harness" / "cache"

    def scan(self, deep: bool = False) -> dict:
        """Scan Unity project and return profile."""
        packages = self._detect_packages()
        profile = {
            "schema": "unity-harness.project-profile.v1",
            "project_path": str(self.project_path),
            "unity_version": self._detect_unity_version(),
            "packages": packages,
            "assemblies": self._detect_assemblies(),
            "tests": self._detect_tests(),
            "scenes": self._detect_scenes(),
            "protected_patterns": self._get_protected_patterns(),
            "serialization_sensitive": self._detect_serialization_sensitive() if deep else [],
            "generated_folders": ["Library", "Temp", "Obj", "Logs", "Builds", "UserSettings"],
            "last_scan_utc": datetime.now(timezone.utc).isoformat(),
        }
        profile.update(collect_unity_facts(self.project_path, packages))
        profile["vfx_semantics"] = detect_vfx_semantics(self.project_path)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self.cache_dir / "project-profile.json"
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)
        return profile

    def _detect_unity_version(self) -> str:
        version_file = self.project_path / "ProjectSettings" / "ProjectVersion.txt"
        if not version_file.exists():
            return "unknown"
        content = version_file.read_text(encoding="utf-8").strip()
        for line in content.splitlines():
            if line.startswith("m_EditorVersion:"):
                return line.split(":", 1)[1].strip()
        return "unknown"

    def _detect_packages(self) -> dict:
        manifest = self.project_path / "Packages" / "manifest.json"
        if not manifest.exists():
            return {}
        with open(manifest, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return data.get("dependencies", {})

    def _detect_assemblies(self) -> list[dict]:
        assemblies = []
        for asmdef in self.project_path.rglob("*.asmdef"):
            if self._is_in_generated_folder(asmdef):
                continue
            try:
                with open(asmdef, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                rel_path = str(asmdef.relative_to(self.project_path))
                platform = "editor" if data.get("includePlatforms", []) == ["Editor"] else "runtime"
                assemblies.append(
                    {
                        "name": data.get("name", asmdef.stem),
                        "path": rel_path,
                        "platform": platform,
                        "references": data.get("references", []),
                        "include_platforms": data.get("includePlatforms", []),
                        "exclude_platforms": data.get("excludePlatforms", []),
                        "define_constraints": data.get("defineConstraints", []),
                        "auto_referenced": data.get("autoReferenced", True),
                        "allowUnsafeCode": data.get("allowUnsafeCode", False),
                    }
                )
            except (json.JSONDecodeError, OSError):
                continue
        return assemblies

    def _detect_tests(self) -> dict:
        test_asmdefs = []
        for asmdef in self.project_path.rglob("*.asmdef"):
            try:
                with open(asmdef, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                is_editor_only = data.get("includePlatforms") == ["Editor"]
                is_test_assembly = "test" in data.get("name", "").lower()
                if is_editor_only and is_test_assembly:
                    test_asmdefs.append(str(asmdef.relative_to(self.project_path)))
            except (json.JSONDecodeError, OSError):
                continue
        has_test_framework = "com.unity.test-framework" in self._detect_packages()
        return {
            "editModeAvailable": len(test_asmdefs) > 0 or has_test_framework,
            "playModeAvailable": has_test_framework,
            "test_asmdefs": test_asmdefs,
        }

    def _detect_scenes(self) -> list[str]:
        scenes = []
        build_settings = self.project_path / "ProjectSettings" / "EditorBuildSettings.asset"
        if build_settings.exists():
            content = build_settings.read_text(encoding="utf-8")
            for line in content.splitlines():
                if "path:" in line:
                    path = line.split("path:", 1)[1].strip().strip('"')
                    scenes.append(path)
        for unity_file in self.project_path.rglob("*.unity"):
            if self._is_in_generated_folder(unity_file):
                continue
            rel = str(unity_file.relative_to(self.project_path))
            if rel not in scenes:
                scenes.append(rel)
        return scenes

    def _get_protected_patterns(self) -> list[str]:
        protected = self.config.get("protected_files", {})
        patterns = []
        patterns.extend(protected.get("block_direct_write", []))
        patterns.extend(protected.get("escalate_direct_write", []))
        patterns.extend(protected.get("never_touch", []))
        return patterns

    def _detect_serialization_sensitive(self) -> list[dict]:
        import re

        results = []
        for cs_file in self.project_path.rglob("*.cs"):
            if self._is_in_generated_folder(cs_file):
                continue
            try:
                content = cs_file.read_text(encoding="utf-8")
                if "MonoBehaviour" in content or "ScriptableObject" in content:
                    fields = []
                    for line in content.splitlines():
                        line_stripped = line.strip()
                        if line_stripped.startswith("[") or line_stripped.startswith("//"):
                            continue
                        if (
                            "SerializeField" in line_stripped
                            or "SerializeReference" in line_stripped
                        ):
                            fields.append(line_stripped)
                        match = re.match(r"public\s+\w+\s+(\w+)\s*[;=]", line_stripped)
                        if match:
                            fields.append(match.group(1))
                    if fields:
                        script_type = (
                            "MonoBehaviour" if "MonoBehaviour" in content else "ScriptableObject"
                        )
                        results.append(
                            {
                                "file": str(cs_file.relative_to(self.project_path)),
                                "type": script_type,
                                "serialized_fields": fields[:20],
                            }
                        )
            except OSError:
                continue
        return results[:50]

    def _is_in_generated_folder(self, path: Path) -> bool:
        parts = path.relative_to(self.project_path).parts
        generated = {"Library", "Temp", "Obj", "Logs", "Builds", "UserSettings", ".vs"}
        return bool(generated & set(parts))

    def write_memory_files(self, profile: dict):
        """Write UNITY_AGENTS.md files near relevant code domains."""
        memories = self._generate_domain_memories(profile)
        for domain_path, content in memories.items():
            target = self.project_path / domain_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    def _generate_domain_memories(self, profile: dict) -> dict[str, str]:
        memories = {}
        root_content = [
            "# UNITY_AGENTS.md",
            "Scope: Project root",
            f"Unity version: {profile.get('unity_version', 'unknown')}",
            "",
            "## Stable facts",
        ]
        for pkg_name, pkg_ver in list(profile.get("packages", {}).items())[:10]:
            root_content.append(f"- Package: {pkg_name} ({pkg_ver})")
        if profile.get("assemblies"):
            root_content.append("")
            root_content.append("## Assembly graph")
            for asm in profile["assemblies"]:
                refs = ", ".join(asm.get("references", [])[:5])
                root_content.append(f"- {asm['name']} ({asm['platform']}) refs: [{refs}]")
        root_content.extend(
            [
                "",
                "## Protected patterns",
                "- Do not edit .meta, .unity, .prefab, .asset, .controller, .anim directly.",
                "- Do not edit Library/, Temp/, Obj/, Logs/, Builds/, UserSettings/.",
                "",
                "## Verification",
                "- Run compile/import when Unity is available.",
                "- Run EditMode tests for logic changes.",
                "- Report manual Inspector checks for asset changes.",
            ]
        )
        memories["AGENTS.md"] = "\n".join(root_content)
        return memories
