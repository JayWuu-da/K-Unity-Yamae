# K-Unity-Yamae Release Checklist

## Local Quality Gate

Run before tagging or handing the harness to a Unity production repo:

```bash
python -m pytest -q
python -m ruff check .
```

## Harness Smoke Checks

Use a fixture or disposable Unity project:

```bash
python tests/fixtures/make_unity_project.py --kind ui-graphics-architecture --out .omo/tmp/release-fixture --git-init
kunity-yamae --project .omo/tmp/release-fixture scan --json
kunity-yamae --project .omo/tmp/release-fixture risk "Fix prefab button raycast" --json
kunity-yamae --project .omo/tmp/release-fixture context --pretty "Fix prefab button raycast"
kunity-yamae --project .omo/tmp/release-fixture providers doctor --json
kunity-yamae --project .omo/tmp/release-fixture run "Fix prefab button raycast" --plan-only --verify-dry-run --json
```

## Unity Editor Checks

Only claim these checks when Unity actually ran:

```bash
kunity-yamae --project <unity-project> inspect --editor-probe --json
kunity-yamae --project <unity-project> verify --compile-only
kunity-yamae --project <unity-project> verify --editmode
kunity-yamae --project <unity-project> verify --playmode
```

If Unity is not installed or batchmode fails, report static scan and guard
coverage only.

## Agent Integration Checks

```bash
kunity-yamae --project <unity-project> init-agent --target both --dry-run --json
kunity-yamae --project <unity-project> init-agent --target both --write
```

Confirm generated files:

- `AGENTS.md`
- `CLAUDE.md`
- `.codex/skills/k-unity-yamae/SKILL.md`
- `.claude/commands/kunity-yamae.md`

## Guarded Edit Checks

For Codex/Claude/LazyCodex-style patch handoff:

```bash
kunity-yamae --project <unity-project> propose-edit "Task" --patch-file proposed.diff --json
kunity-yamae --project <unity-project> propose-edit "Task" --patch-file proposed.diff --apply --json
kunity-yamae --project <unity-project> guard-diff --json
```

Hard failures must block application or roll back the patch.
