# unity.serialized-field-rename

**Trigger:**
- A public field in MonoBehaviour/ScriptableObject is renamed.
- A [SerializeField] or [SerializeReference] field is renamed.
- A serializable class field reachable from Unity objects is renamed.

**Required:**
- Add [FormerlySerializedAs("oldName")] on the new field unless intentionally dropping serialized data.
- Report the old name, new name, declaring type, and affected assets if discoverable.
- Run compile/import verification if Unity is available.

**Forbidden:**
- Do not manually rewrite scene/prefab YAML to force migration.
- Do not claim Inspector values are preserved unless a migration path exists.
