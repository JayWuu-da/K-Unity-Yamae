"""Serialized field rename detector - catches field renames that break serialization."""

import re
from pathlib import Path


class SerializationGuard:
    def __init__(self, project_path: Path, config: dict):
        self.project_path = project_path
        self.config = config
        self.ser_config = config.get("serialization", {})

    def check(self, old_content: str, new_content: str, file_path: str) -> list[dict]:
        """Compare old and new C# content for serialized field renames."""
        issues = []

        old_fields = self._extract_serialized_fields(old_content)
        new_fields = self._extract_serialized_fields(new_content)

        old_field_names = {f["name"] for f in old_fields}
        new_field_names = {f["name"] for f in new_fields}

        removed = old_field_names - new_field_names
        added = new_field_names - old_field_names

        for removed_name in removed:
            old_field = next(f for f in old_fields if f["name"] == removed_name)
            candidate = self._find_rename_candidate(removed_name, old_field, added, new_fields)
            if candidate:
                new_field = next(f for f in new_fields if f["name"] == candidate)
                has_migration = self._has_formerly_serialized_as(
                    new_content, candidate, removed_name
                )
                if not has_migration:
                    issues.append(
                        {
                            "guard": "serialized_rename",
                            "severity": "hard_failure",
                            "file": file_path,
                            "message": (
                                f"Field '{removed_name}' renamed to '{candidate}' "
                                f"in {old_field['declaring_type']} without "
                                f'[FormerlySerializedAs("{removed_name}")]. '
                                "Inspector values will be lost."
                            ),
                            "old_name": removed_name,
                            "new_name": candidate,
                            "declaring_type": old_field["declaring_type"],
                            "migration_present": False,
                        }
                    )
                else:
                    issues.append(
                        {
                            "guard": "serialized_rename",
                            "severity": "info",
                            "file": file_path,
                            "message": (
                                f"Field '{removed_name}' renamed to '{candidate}' "
                                f"in {old_field['declaring_type']} with "
                                "[FormerlySerializedAs] migration."
                            ),
                            "old_name": removed_name,
                            "new_name": candidate,
                            "declaring_type": old_field["declaring_type"],
                            "migration_present": True,
                        }
                    )
            else:
                if old_field.get("is_serialized"):
                    issues.append(
                        {
                            "guard": "serialized_rename",
                            "severity": "warning",
                            "file": file_path,
                            "message": f"Serialized field '{removed_name}' removed from "
                            f"{old_field['declaring_type']}. Possible data removal.",
                            "old_name": removed_name,
                            "declaring_type": old_field["declaring_type"],
                        }
                    )

        for added_name in added:
            new_field = next(f for f in new_fields if f["name"] == added_name)
            removed_match = self._find_reverse_candidate(added_name, new_field, removed, old_fields)
            if removed_match and not self._has_formerly_serialized_as(
                new_content, added_name, removed_match
            ):
                issues.append(
                    {
                        "guard": "serialized_rename",
                        "severity": "hard_failure",
                        "file": file_path,
                        "message": f"Field '{removed_match}' likely renamed to '{added_name}' "
                        f"in {new_field['declaring_type']} without [FormerlySerializedAs].",
                        "old_name": removed_match,
                        "new_name": added_name,
                        "declaring_type": new_field["declaring_type"],
                        "migration_present": False,
                    }
                )

        return issues

    def _extract_serialized_fields(self, content: str) -> list[dict]:
        fields = []
        current_type = ""
        in_serializable = False

        for line in content.splitlines():
            stripped = line.strip()

            type_match = re.match(
                r"(?:public|internal|private)\s+(?:sealed\s+)?class\s+(\w+)\s*(?::\s*([^{]+))?",
                stripped,
            )
            if type_match:
                current_type = type_match.group(1)
                base = type_match.group(2) or ""
                in_serializable = "System.Serializable" in base
                rest_of_line = stripped[type_match.end() :]
                if rest_of_line.strip().startswith("{"):
                    rest_of_line = rest_of_line[rest_of_line.index("{") + 1 :]
                field_matches = re.findall(
                    r"(?:\[.*?\]\s*)*(?:public|private|protected)\s+([\w<>\[\],\s]+)\s+(\w+)\s*[;=]",
                    rest_of_line,
                )
                for ftype, fname in field_matches:
                    has_ser = (
                        "[SerializeField]" in rest_of_line or "[SerializeReference]" in rest_of_line
                    )
                    is_public = bool(re.search(r"public\s+", rest_of_line))
                    fields.append(
                        {
                            "name": fname,
                            "type": ftype.strip(),
                            "declaring_type": current_type,
                            "is_serialized": has_ser or is_public,
                            "line": rest_of_line.strip()[:100],
                        }
                    )
                continue

            if stripped.startswith("[System.Serializable]"):
                in_serializable = True
                continue

            is_mono = "MonoBehaviour" in content or "ScriptableObject" in content
            has_serialize_ref = "[SerializeField]" in stripped or "[SerializeReference]" in stripped
            is_public_field = bool(re.match(r"public\s+\w+\s+\w+\s*[;=]", stripped))

            if (is_mono or in_serializable) and (has_serialize_ref or is_public_field):
                field_match = re.match(
                    r"(?:\[.*?\]\s*)*(?:public|private|protected)\s+([\w<>\[\],\s]+)\s+(\w+)\s*[;=]",
                    stripped,
                )
                if field_match:
                    field_type = field_match.group(1).strip()
                    field_name = field_match.group(2)
                    fields.append(
                        {
                            "name": field_name,
                            "type": field_type,
                            "declaring_type": current_type or "unknown",
                            "is_serialized": has_serialize_ref or is_public_field,
                            "line": stripped,
                        }
                    )

        return fields

    def _find_rename_candidate(
        self, removed_name: str, old_field: dict, added_names: set, new_fields: list
    ) -> str | None:
        old_type = old_field.get("type", "")
        candidates = []
        for new_name in added_names:
            new_field = next(f for f in new_fields if f["name"] == new_name)
            if new_field.get("type", "") == old_type:
                if new_field.get("declaring_type") == old_field.get("declaring_type"):
                    candidates.append((new_name, 0))
                else:
                    candidates.append((new_name, 1))
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0] if candidates else None

    def _find_reverse_candidate(
        self, added_name: str, new_field: dict, removed_names: set, old_fields: list
    ) -> str | None:
        new_type = new_field.get("type", "")
        for removed_name in removed_names:
            old_field = next(f for f in old_fields if f["name"] == removed_name)
            if old_field.get("type", "") == new_type:
                return removed_name
        return None

    def _has_formerly_serialized_as(self, content: str, field_name: str, old_name: str) -> bool:
        pattern = rf'\[FormerlySerializedAs\s*\(\s*"{re.escape(old_name)}"\s*\)\s*\]'
        idx = content.find(field_name)
        if idx < 0:
            return False
        preceding = content[max(0, idx - 300) : idx]
        return bool(re.search(pattern, preceding))
