# unity.asmdef

**Trigger:**
- Changes to .asmdef or .asmref files.

**Checks:**
- References added/removed.
- includePlatforms/excludePlatforms changed.
- defineConstraints changed.
- allowUnsafeCode changed.
- autoReferenced changed.

**Risk escalation when:**
- A runtime assembly references an Editor-only assembly.
- A test assembly becomes production-referenced.
- A widely referenced core assembly changes name.
- Define constraints remove platform coverage.

**Required evidence:**
- Compile/import verification.
- Graph impact summary.
- Changed assemblies list.
