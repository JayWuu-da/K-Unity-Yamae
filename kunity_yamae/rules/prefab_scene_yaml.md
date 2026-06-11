# unity.prefab-scene-yaml

**Trigger:**
- Direct write to .unity, .prefab, .asset, .controller, .anim, or similar Unity YAML asset.

**Default:**
- Block direct write.

**Allowed only when:**
- Mode is Asset-Safe or Migration.
- The plan explains why Editor API/manual change is not practical.
- The diff report lists object IDs, GUIDs, components, and manual validation steps.

**Required final report:**
- State that manual Unity Editor inspection is required unless a project-specific probe validated the asset.
