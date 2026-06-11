# K-Unity-Yamae Current Analysis

**Date:** June 11, 2026

K-Unity-Yamae is a thin Unity-specific harness for Codex, Claude Code, and other coding agents. It keeps the agent loop light by doing fast static project discovery first, then escalating only when Unity-specific risk appears.

## Implemented Surface

| Area | Current capability |
| --- | --- |
| Project scan | Unity version, packages, assemblies, scenes, tests, protected/generated paths |
| Unity facts | UI system signals, prefab wiring hints, graphics importer settings, platform texture overrides, architecture naming patterns |
| Risk model | Fast Patch, Standard, Asset-Safe, Migration modes with rule-card selection |
| Agent integration | Codex, Claude, Gemini, Kimi, GLM, MiMo, and offline `local-patch` handoff |
| Guarded edits | Unified diff evaluation in a detached git worktree before optional apply |
| Editor probe | Batchmode source for inspector listeners, missing references, prefab overrides, UI component state |
| Verification | Static guards, Unity command planning, Editor probe stage, dry-run reporting |
| Reporting | Evidence ledger, guard reports, release check JSON |

## Unity Focus

The harness is intentionally biased toward production Unity risks:

- `.meta` and GUID continuity
- `.unity`, `.prefab`, `.asset`, `.controller`, `.anim` serialized artifact safety
- `[SerializeField]` rename detection and migration prompts
- runtime versus `UnityEditor` boundary checks
- asmdef dependency impact
- UI prefab wiring, EventSystem/GraphicRaycaster/CanvasGroup signals
- texture, sprite, audio, and model importer settings for mobile and PC decisions
- MVP/MVC/controller/manager/service naming signals without overclaiming ownership

## Current Limits

Editor-level object graph facts require Unity batchmode execution. Static YAML/text inspection is useful for triage, but it cannot fully prove Inspector object references, prefab override intent, or persistent listener target validity. Those claims are only valid when the Editor probe report exists.

Provider execution remains intentionally conservative. API-backed agents can produce text or patches, while the safest automated mutation path is still `run --guarded-agent-patch`, which routes unified diffs through guard evaluation before applying.

## Quality Gates

Release readiness is checked with:

```bash
kunity-yamae release-check --json
python -m pytest -q
python -m ruff check .
```
