# unity.meta-guid

**Trigger:**
- Any .meta file is added, deleted, moved, renamed, or modified.
- Any asset under Assets/ is moved, renamed, added, or deleted.

**Required:**
- Asset and .meta changes must be paired.
- Existing asset GUIDs must not change.
- New assets must have new .meta files.
- Deleted assets must delete corresponding .meta files.
- Moved assets must move corresponding .meta files with the same GUID.

**Failure:**
- Unpaired .meta change is a hard failure.
- Existing GUID change is a hard failure unless an explicit migration override is present.
