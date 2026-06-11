# unity.editor-runtime-boundary

**Trigger:**
- C# file imports UnityEditor namespace.
- File is in an Editor folder or Editor-only assembly.
- Assembly definition references cross Editor/runtime boundary.

**Required:**
- Editor code must be in an Editor folder or Editor-only asmdef.
- Runtime assemblies must not reference Editor assemblies.
- MenuItem and EditorWindow code must not run during player runtime.

**Forbidden:**
- Runtime assembly referencing UnityEditor namespace.
- Editor assembly referenced by production assembly.
