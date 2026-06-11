# unity.resources-addressables

**Trigger:**
- Resources.Load path string changed.
- Addressables.LoadAssetAsync key changed.
- Addressable labels/groups/settings changed.
- Asset moved under or out of a Resources folder.
- Scene name/path changed in build settings.

**Checks:**
- Verify referenced asset path/key still exists when statically discoverable.
- Report build size risk for new Resources assets.
- Require PlayMode or custom probe for runtime lookup paths when possible.

**Forbidden:**
- Changing Resources paths without verifying callers.
- Changing Addressables keys without updating all references.
