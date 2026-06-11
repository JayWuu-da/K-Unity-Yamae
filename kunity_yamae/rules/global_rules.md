# Unity Harness Global Rules

1. Classify Unity risk before editing.
2. Keep changes minimal and scoped to the task.
3. Never edit Library, Temp, Obj, Logs, Builds, or UserSettings.
4. Never directly write .meta, .unity, .prefab, .asset, .controller, or .anim files unless the selected mode explicitly permits it.
5. Preserve .meta files and GUID continuity for asset create/move/rename/delete operations.
6. Treat serialized field/class/asset renames as migrations.
7. Keep UnityEditor code out of runtime assemblies.
8. Report actual verification performed and manual checks still required.
