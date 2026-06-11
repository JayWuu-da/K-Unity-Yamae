# K-Unity-Yamae Upgrade Report

**Date:** June 11, 2026

## Completed Upgrade Themes

| Theme | Result |
| --- | --- |
| Codex and Claude usability | `install`, `init-agent`, project-local prompts, and CLI entrypoints are available |
| LazyCodex-style handoff | `local-patch` and `run --guarded-agent-patch` support patch-first guarded execution |
| Unity production context | Rule cards, risk model, context pack, UI/graphics/architecture facts, and manual check prompts are wired |
| Editor inspection | Probe source can emit inspector listeners, missing references, prefab overrides, and UI component state |
| Provider diagnostics | Provider doctor reports readiness without forcing all providers to be installed |
| Release operability | `release-check --json` reports package data and required quality gates |

## Remaining High-Value Work

1. Add real streaming/tool-loop adapters for Codex and Claude Code APIs.
2. Expand Unity Editor probe coverage for Addressables, animation controller transitions, material/shader variants, and prefab override value diffs.
3. Add packaging metadata for a distributable wheel and optional Codex plugin bundle.
4. Add golden fixture projects for URP/HDRP, mobile texture compression, localization tables, Addressables, and large UI prefab sets.
5. Add CI that runs release-check, pytest, ruff, and source-level Editor probe compilation checks.

## Recommended Operating Mode

For live-service Unity projects, keep the default loop lightweight:

```bash
kunity-yamae scan
kunity-yamae run "task" --plan-only --verify-dry-run --editor-probe
kunity-yamae run "task" --guarded-agent-patch
kunity-yamae verify --dry-run
```

Only run Unity batchmode compile, EditMode, PlayMode, or build validation when the risk score, touched files, or release gate requires it.
