# Unity Execution Path Rule Card

**Trigger:**
- UI, popup, button, shortcut, controller, tab, or lock-condition work where the visible owner may differ from the named file.

**Required:**
- Trace the real user path before editing: entry point, open/create call, prefab or persistent listener binding, controller reset, lock conditions, and final renderer.
- Separate active, unused, conditionally exposed, direct-entry, and compile-out surfaces when similar old and new UI paths exist.
- Prefer the runtime owner or controller path over direct prefab YAML edits.

**Forbidden:**
- Do not infer ownership from file names alone.
- Do not patch a similar popup or controller until its actual entry route is proven.

**Required evidence:**
- A route summary naming the entry point, owner controller, prefab or listener binding, and final displayed surface.
