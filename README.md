# K-Unity-Yamae

**A thin, risk-adaptive Unity agent harness for AI coding agents.**

K-Unity-Yamae is a Python-based safety layer that wraps AI coding agents (Codex, Claude, Gemini, Kimi, GLM, MiMo) with Unity-specific guardrails. It classifies each task by Unity-specific risk, injects only the relevant rule cards, protects serialized artifacts via guards, runs Unity batchmode verification, and produces evidence-tracked completion reports.

---

## Table of Contents

- [Philosophy](#philosophy)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Commands](#cli-commands)
- [Risk Model](#risk-model)
- [Risk Modes](#risk-modes)
- [Unity Guards](#unity-guards)
- [Verification Tiers](#verification-tiers)
- [Agent Backends](#agent-backends)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Rule Cards](#rule-cards)
- [Evidence Ledger](#evidence-ledger)
- [Unity Editor Integration](#unity-editor-integration)
- [Adding a Custom Agent](#adding-a-custom-agent)
- [Examples](#examples)
- [Inspired By](#inspired-by)
- [License](#license)

---

## Philosophy

> Adopt the discipline, not the ceremony.

- **Low-risk C# edits should be fast.** No mandatory deep interview or full planning loop for a typo fix.
- **Asset/serialization changes should be strict.** Strong guardrails for .meta, .unity, .prefab, .asset, .asmdef, and serialized fields.
- **Verification must be honest.** Never claim Editor or Play Mode validation unless it actually ran.
- **One writer at a time.** Parallel read-only analysis is fine; parallel asset mutation is not.
- **Report what you did, not what you hoped happened.**

---

## Architecture

```
User Task
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                  Task Intake                             │
│           Normalize task, detect intent                  │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              Unity Project Scanner                       │
│  Detect: version, packages, assemblies, scenes, tests   │
│  Cache: .unity-harness/project-profile.json             │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                Risk Classifier                           │
│  Input: task text + git diff + project profile          │
│  Output: risk_score (0-100), mode, triggers, rules      │
│                                                         │
│  ┌──────────┬──────────┬──────────┬──────────┐          │
│  │ 0-29     │ 30-59    │ 60-79    │ 80-100   │          │
│  │ Fast     │ Standard │ Asset    │ Migration│          │
│  │ Patch    │          │ Safe     │          │          │
│  └──────────┴──────────┴──────────┴──────────┘          │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              Context Selector                            │
│  Select: relevant files, rule cards, project memory     │
│  Inject: file previews, Unity-specific guidance         │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│            Execution Controller                          │
│  One writer agent at a time                             │
│  Optional read-only scouts for analysis                 │
│                                                         │
│  ┌─────────┬─────────┬─────────┬─────────┬─────────┐   │
│  │ Codex   │ Claude  │ Gemini  │ Kimi    │ MiMo    │   │
│  │ GPT-4o  │ Sonnet  │ 2.5     │ 128K    │ auto    │   │
│  └─────────┴─────────┴─────────┴─────────┴─────────┘   │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│          File Guard / Diff Guard                         │
│  Intercept edits, apply Unity-specific guards:          │
│  • Meta guard: .meta pairing, GUID continuity           │
│  • YAML guard: block protected file writes              │
│  • Serialization guard: detect field renames            │
│  • Boundary guard: Editor/runtime separation            │
│  • Asmdef guard: assembly graph impact                  │
│  • Addressables guard: string-key path changes          │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              Unity Verifier                              │
│  Tier 0: Static guards only                             │
│  Tier 1: Unity batchmode compile/import                 │
│  Tier 2: EditMode tests                                 │
│  Tier 3: PlayMode tests                                 │
│  Tier 4: Custom Editor probes (-executeMethod)          │
│  Tier 5: Build validation                               │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│             Evidence Ledger                              │
│  Append-only JSONL event log                            │
│  Records: file changes, guard results, verification,    │
│           commands, manual checks, errors                │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│            Completion Report                             │
│  Output: markdown + JSON                                │
│  Sections: summary, changed files, risk decisions,      │
│            guards run, verification tiers, manual checks │
└─────────────────────────────────────────────────────────┘
```

---

## Installation

### From Source (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-org/K-Unity-Yamae.git
cd K-Unity-Yamae

# Install in development mode
pip install -e .

# Install with agent SDK dependencies
pip install -e ".[agents]"

# Install with dev dependencies
pip install -e ".[dev]"
```

### Dependencies

**Core dependencies** (always installed):
- `pyyaml>=6.0` - YAML config parsing
- `click>=8.0` - CLI framework
- `rich>=13.0` - Terminal formatting

**Agent dependencies** (optional, install with `pip install -e ".[agents]"`):
- `openai>=1.0` - OpenAI Codex adapter
- `anthropic>=0.30` - Claude adapter
- `google-genai>=0.3` - Gemini adapter

Kimi, GLM, and MiMo agents use `urllib.request` (Python stdlib) and need no extra packages.

### Requirements

- Python >= 3.10
- Git (for diff guards and git status checks)
- Unity Editor (for verification tiers 1-5, optional for tier 0)

---

## Quick Start

### 0. Install Codex and Claude Code entrypoints

```bash
kunity-yamae install --codex --claude
kunity-yamae init-agent --target both --write
```

This writes repo-local entry files for Codex and Claude Code so both agents can call the same Unity-aware harness instead of relying on a long pasted prompt.

### 1. Scan your Unity project

```bash
kunity-yamae scan --project /path/to/your/unity/project
```

This detects Unity version, packages, assemblies, scenes, and protected paths. Results are cached to `.unity-harness/project-profile.json`.

### 2. Classify task risk

```bash
kunity-yamae risk "Rename PlayerStats.hitpoints to health"
```

Output:
```
╭─ Risk Report ─────╮
│ Task    │ Rename PlayerStats.hitpoints to health
│ Score   │ 80
│ Mode    │ migration
│ Triggers│ Serialized field/class rename
│ Rules   │ unity.serialized-field-rename
╰───────────────────╯
```

### 3. Run the full pipeline

```bash
kunity-yamae run "Fix enemy spawn delay bug" --agent claude
```

This runs the complete pipeline: risk classification -> agent execution -> guard checks -> verification -> report.

### 4. Individual commands

```bash
# Build a task context pack for Codex/Claude
kunity-yamae context --pretty "Fix UI raycast and Android texture compression"

# Get a lightweight, non-mutating run plan
kunity-yamae run "Fix ShopPresenter button raycast" --plan-only --verify-dry-run --json

# Validate a proposed unified diff before applying it
kunity-yamae propose-edit "Fix ShopPresenter" --patch-file proposed.diff --json
kunity-yamae propose-edit "Fix ShopPresenter" --patch-file proposed.diff --apply --json

# Inspect hierarchy, prefabs, UI, and graphics import facts
kunity-yamae inspect --json

# Run Unity Editor API probe first, then merge richer Inspector facts
kunity-yamae inspect --editor-probe --json

# Diagnose provider env vars and SDK availability
kunity-yamae providers doctor --json

# Run task through a specific agent
kunity-yamae work "Fix null check in DamageCalculator" --agent codex

# Run verification only
kunity-yamae verify --compile-only
kunity-yamae verify --editmode
kunity-yamae verify --playmode

# Check git diff for Unity hazards
kunity-yamae guard-diff

# View last report
kunity-yamae report --last
```

---

## CLI Commands

### `kunity-yamae install`

Write lightweight repo-local entrypoints for Codex and Claude Code.

```bash
kunity-yamae install --codex --claude
kunity-yamae install          # defaults to both
kunity-yamae install --codex  # Codex skill only
kunity-yamae install --claude # Claude command only
```

**Output:** `.codex/skills/k-unity-yamae/SKILL.md` and/or `.claude/commands/kunity-yamae.md`.

### `kunity-yamae scan`

Build or refresh the Unity project profile.

```bash
kunity-yamae scan --project ./MyUnityGame
kunity-yamae scan --deep          # Include assembly graph analysis
kunity-yamae scan --write-memory  # Write UNITY_AGENTS.md files
kunity-yamae scan --json          # Machine-readable profile
```

**Output:** Project version, packages, assemblies, scenes, protected patterns.

### `kunity-yamae context`

Build the compact task context pack used before a Codex or Claude Code edit.

```bash
kunity-yamae context --pretty "Fix UI raycast and Android texture compression"
kunity-yamae context --deep --pretty "Audit prefab hierarchy and scene references"
```

**Output:** JSON with risk mode, rule cards, selected Unity facts, relevant files, and manual checks.

### `kunity-yamae risk`

Classify task risk before mutation.

```bash
kunity-yamae risk "Rename PlayerStats.hitpoints to health"
kunity-yamae risk --diff  # Include current git diff in classification
kunity-yamae risk "Fix prefab button raycast" --json
```

**Output:** Risk score (0-100), mode, triggers, required rule cards, blocked operations, verification plan.

### `kunity-yamae inspect`

Inspect hierarchy, prefab, UI, and graphics import facts without editing the project.

```bash
kunity-yamae inspect --json
kunity-yamae inspect --editor-probe --json
```

**Output:** Scene count, prefab instance count, missing script prefab count, EventSystem/GraphicRaycaster counts, texture platform overrides, render pipeline, input system, and `editor_probe` status. With `--editor-probe`, the harness temporarily stages its Editor probe under `Assets/Editor/KUnityYamaeHarness/`, runs `KUnityYamae.Editor.HarnessChecks.RunEditorInspection` in batchmode, merges persistent listener targets, prefab override counts, and missing serialized object references from `.unity-harness/reports/editor-inspection.json`, then removes the staged probe files.

### `kunity-yamae providers doctor`

Diagnose configured provider readiness for Codex, Claude, Gemini, Kimi, GLM, and MiMo.

```bash
kunity-yamae providers doctor --json
```

**Output:** Env var, key presence, SDK availability, readiness status, and the `kunity-yamae run --agent ...` usage command per provider.

`--live` is opt-in. Without it, provider doctor does not call external APIs; it only checks config, env vars, and local SDK availability.

### `kunity-yamae work`

Run a task through the selected agent backend.

```bash
kunity-yamae work "Fix enemy spawn delay" --agent claude
kunity-yamae work "Add health bar UI" --mode standard --agent codex
```

**Options:**
- `--agent` - Agent backend (codex, claude, gemini, kimi, glm, mimo)
- `--mode` - Force a specific mode (fast_patch, standard, asset_safe, migration)
- `--auto` - Auto-select mode from risk score

### `kunity-yamae run`

Run the full pipeline (risk -> work -> verify -> guard -> report).

```bash
kunity-yamae run "Rename PlayerStats.hitpoints to health" --agent claude
kunity-yamae run "Fix typo in comments" --agent mimo --no-verify --no-guard
kunity-yamae run "Fix UI button" --plan-only --verify-dry-run --json
```

**Options:**
- `--agent` - Agent backend
- `--verify` / `--no-verify` - Enable/disable verification (default: enabled)
- `--guard` / `--no-guard` - Enable/disable guard checks (default: enabled)
- `--plan-only` - Build scan/risk/context/guard/verify plan without agent execution
- `--provider-check` - Fail fast when the selected provider is not ready
- `--verify-dry-run` - Include Unity command lines without launching Unity

### `kunity-yamae verify`

Run Unity-aware checks without editing.

```bash
kunity-yamae verify --compile-only
kunity-yamae verify --editmode
kunity-yamae verify --playmode
kunity-yamae verify --build StandaloneWindows64
kunity-yamae verify --custom-method Company.Project.Editor.HarnessChecks.RunAll
kunity-yamae verify --compile-only --dry-run --json
```

### `kunity-yamae guard-diff`

Inspect current git diff for Unity-specific hazards.

```bash
kunity-yamae guard-diff
kunity-yamae guard-diff --json
```

**Checks:** Meta pairing, GUID continuity, YAML writes, Editor/runtime boundaries, asmdef changes, Addressables paths.

### `kunity-yamae propose-edit`

Validate a unified diff in a temporary git worktree before applying it to the real project.

```bash
kunity-yamae propose-edit "Fix UI raycast" --patch-file proposed.diff --json
kunity-yamae propose-edit "Fix UI raycast" --patch-file proposed.diff --apply --json
```

**Output:** `unity-harness.proposed-edit.v1` with `ready_to_apply`, `blocked`, `invalid_patch`, `applied`, or `rolled_back`. Hard failures from Unity guards block application.

### `kunity-yamae report`

Show the last task report.

```bash
kunity-yamae report --last
```

---

## Risk Model

### Risk Score Calculation

```
risk_score = min(100, file_risk + action_risk + semantic_unity_risk)
```

### File Risk Table

| File Pattern | Base Risk | Reason |
|-------------|-----------|--------|
| `Assets/**/*.cs` | +10 to +45 | C# varies from low to high risk |
| `Assets/**/*.asmdef` | +55 | Changes compile graph |
| `Assets/**/*.asmref` | +55 | Changes compile graph |
| `Assets/**/*.meta` | +80 | Contains GUID/import metadata |
| `Assets/**/*.unity` | +85 | Scene serialization |
| `Assets/**/*.prefab` | +85 | Prefab serialization |
| `Assets/**/*.asset` | +70 | ScriptableObject/settings |
| `Assets/**/*.controller` | +75 | Animator serialization |
| `Assets/**/*.anim` | +75 | Animation serialization |
| `ProjectSettings/**` | +80 | Global project behavior |
| `Packages/manifest.json` | +75 | Package versions |

### Semantic Unity Triggers

| Trigger | Risk Score | Example Tasks |
|---------|-----------|---------------|
| Serialized field rename | +70 | "Rename hitpoints to health" |
| MonoBehaviour lifecycle | +20 | "Add start delay to spawner" |
| Editor/runtime boundary | +25 | "Add custom inspector" |
| Resources/Addressables | +30 | "Change Resources.Load path" |
| Assembly definition | +50 | "Change asmdef references" |
| Package/settings change | +45 | "Upgrade Input System" |
| Asset move | +50 | "Move prefabs to new folder" |
| YAML edit | +55 | "Edit prefab YAML" |

### Action Risk Modifiers

| Action | Risk | Examples |
|--------|------|----------|
| Fix/bug/typo | +5 | "Fix null check", "Fix typo" |
| Add/create/implement | +15 | "Add health bar", "Implement damage" |
| Refactor/restructure | +25 | "Refactor combat system" |
| Default | +10 | Any other task |

---

## Risk Modes

| Mode | Score Range | Plan Required | Guards Active | Verification |
|------|-------------|---------------|---------------|-------------|
| **Fast Patch** | 0-29 | No | Minimal | Static only |
| **Standard** | 30-59 | Short | Relevant rules | Compile/import |
| **Asset-Safe** | 60-79 | Required | Active | Compile + tests |
| **Migration** | 80-100 | Detailed | Full | All tiers |

### Mode Behaviors

**Fast Patch (0-29):**
- No planning required
- Minimal rule injection
- Quick C# edits only
- Static guards run
- Compile check if cheap/available

**Standard (30-59):**
- Short plan recommended
- Relevant Unity rules injected
- MonoBehaviour/UI/gameplay edits
- Compile/import check recommended
- Targeted tests if available

**Asset-Safe (60-79):**
- Plan required
- Protected-file guard active
- Prefab/scene references, asmdef edits
- Editor tools touching assets
- Verification required or explicit manual-check gap

**Migration (80-100):**
- Detailed migration plan required
- Full guardrails active
- Rollback strategy needed
- Strong evidence requirements
- Manual review checklist required

---

## Unity Guards

### Meta Guard

Ensures .meta files stay paired with assets and validates GUID continuity.

```python
# Checks performed:
- Asset added without matching .meta file -> hard_failure
- Asset deleted without deleting .meta -> warning
- .meta deleted without deleting asset -> warning
- .meta added without matching asset -> hard_failure
- GUID changed in .meta file -> hard_failure
- GUID removed from .meta file -> hard_failure
```

### YAML Guard

Blocks or warns on direct writes to protected Unity YAML artifacts.

**Protected extensions:** `.unity`, `.prefab`, `.asset`, `.controller`, `.anim`, `.overrideController`, `.playable`

| Mode | Behavior |
|------|----------|
| Fast Patch / Standard | `hard_failure` - Block |
| Asset-Safe / Migration | `warning` - Allow with caution |

### Serialization Guard

Detects serialized field renames and checks for `[FormerlySerializedAs]` migration attributes.

```python
# Detects:
- Public field renamed in MonoBehaviour/ScriptableObject
- [SerializeField] field renamed
- Field renamed without [FormerlySerializedAs]
- Field removed (possible data loss)
```

### Boundary Guard

Prevents UnityEditor references in runtime assemblies.

```python
# Detects:
- using UnityEditor outside Editor folder/asmdef
- Fully-qualified UnityEditor usage without #if UNITY_EDITOR
- [MenuItem], [ContextMenu], [CustomEditor], [InitializeOnLoad] in runtime code
- Runtime assembly referencing Editor assembly via asmdef
```

### Asmdef Guard

Detects assembly definition changes and their graph impact.

```python
# Checks:
- Runtime assembly referencing Editor assembly
- Platform include/exclude changes
- Define constraint changes
- Unsafe code enabled
- Auto-referenced changes
- Graph impact (direct + transitive references)
```

### Addressables Guard

Flags Resources/Addressables string-key path changes.

```python
# Detects:
- Resources.Load("...") path changed
- Addressables.LoadAssetAsync key changed
- Asset moved under/out of Resources folder
- Scene name/path changed in build settings
```

### Diff Guard

Orchestrator that runs all guards against the current git diff.

```python
# Runs:
1. Meta guard (git status for add/delete/move)
2. Meta guard (GUID continuity in diff)
3. YAML guard (protected file writes in diff)
4. Addressables guard (path changes in diff)
5. Boundary guard (Editor/runtime violations in changed .cs files)
6. Asmdef guard (assembly definition changes)
```

---

## Verification Tiers

| Tier | Name | Command | What it Proves |
|------|------|---------|---------------|
| 0 | Static | Guards only | No textual hazards |
| 1 | Compile | `Unity -batchmode -quit` | Scripts compile |
| 2 | EditMode | `Unity -runTests -testPlatform EditMode` | Editor logic works |
| 3 | PlayMode | `Unity -runTests -testPlatform PlayMode` | Runtime behavior works |
| 4 | Custom | `Unity -executeMethod HarnessChecks.RunAll` | Project invariants pass |
| 5 | Build | `Unity -buildTarget X` | Build pipeline works |
| M | Manual | Inspector/scene check | Visual verification |

### Verification by Mode

| Mode | Minimum | Recommended | Manual |
|------|---------|-------------|--------|
| Fast Patch | Static | Compile | Usually none |
| Standard | Static + compile | EditMode tests | PlayMode if lifecycle changed |
| Asset-Safe | Static + compile | EditMode + PlayMode | Required for asset changes |
| Migration | Static + compile + migration checks | EditMode + PlayMode + build | Required |

---

## Agent Backends

### Supported Agents

| Backend | Model | Env Variable | SDK Required |
|---------|-------|-------------|-------------|
| **Codex** | gpt-4o | `OPENAI_API_KEY` | `openai>=1.0` |
| **Claude** | claude-sonnet-4-20250514 | `ANTHROPIC_API_KEY` | `anthropic>=0.30` |
| **Gemini** | gemini-2.5-flash | `GOOGLE_API_KEY` | `google-genai>=0.3` |
| **Kimi** | moonshot-v1-128k | `KIMI_API_KEY` | None (urllib) |
| **GLM** | glm-4-plus | `ZHIPU_API_KEY` | None (urllib) |
| **MiMo** | mimo-auto | `MIMO_API_KEY` | None (urllib) |

### Agent Configuration

Each agent backend supports these configuration options in `config/default.yml`:

```yaml
agents:
  default: mimo  # Default agent when --agent is not specified
  backends:
    codex:
      enabled: true
      model: gpt-4o
      api_key_env: OPENAI_API_KEY
      temperature: 0.2
      max_retries: 3
    claude:
      enabled: true
      model: claude-sonnet-4-20250514
      api_key_env: ANTHROPIC_API_KEY
      temperature: 0.2
      max_tokens: 16384
      max_retries: 3
    kimi:
      enabled: true
      model: moonshot-v1-128k
      api_key_env: KIMI_API_KEY
      endpoint: "https://api.moonshot.cn/v1/chat/completions"
      temperature: 0.2
      timeout: 120
      max_retries: 3
```

### Agent Routing Strategy

| Task Type | Risk Mode | Recommended Agent | Reason |
|-----------|-----------|-------------------|--------|
| Low-risk C# fix | Fast Patch | MiMo / GLM | Fast, cheap, sufficient quality |
| MonoBehaviour logic | Standard | Codex (GPT-4o) | Good balance of quality and speed |
| Serialized field rename | Migration | Claude (Sonnet) | Best at careful serialization reasoning |
| Asset move/rename | Migration | Claude (Opus) | Highest accuracy for dangerous operations |
| asmdef graph change | Migration | Codex (GPT-4o) | Good at graph analysis |
| Editor script | Standard | Any | All agents handle this well |
| Full project scan | Any | Kimi (128K) | Long context handles large projects |

### Retry Logic

All agents implement exponential backoff retry:

- **Max retries:** Configurable per agent (default: 3)
- **Backoff:** 2^attempt seconds (1s, 2s, 4s)
- **Retried errors:** 429 (rate limit), 500/502/503 (server errors), timeouts, connection errors

---

## Configuration

### Configuration Hierarchy

```
config/default.yml           (built-in defaults)
        ↓ overridden by
.unity-harness/config.yml    (project-specific)
        ↓ overridden by
--config <path>              (CLI override)
        ↓ overridden by
Environment variables        (${VAR} resolution)
```

### Project-Specific Configuration

Create `.unity-harness/config.yml` in your Unity project root:

```yaml
harness:
  default_mode: auto
  git_diff_timeout: 30

unity:
  executable: auto  # or full path to Unity
  allow_batchmode: true
  custom_validation_method: Company.Project.Editor.HarnessChecks.RunAll

risk:
  low_max: 29
  standard_max: 59
  asset_safe_max: 79
  migration_min: 80

verification:
  timeouts:
    compile: 300
    tests: 600
    build: 1800

agents:
  default: claude
  backends:
    claude:
      model: claude-opus-4-20250514
      max_tokens: 32768
```

### All Configuration Keys

See `config/default.yml` for the complete configuration reference.

**Key sections:**
- `harness` - General harness settings
- `unity` - Unity project and executable settings
- `risk` - Risk score thresholds
- `protected_files` - File patterns to protect
- `file_risk_scores` - Risk scores per file pattern
- `verification` - Verification timeouts and behavior
- `serialization` - Serialization detection settings
- `context` - Context selection limits
- `scanner` - Scanner truncation limits
- `reporting` - Report generation settings
- `agents` - Agent backend configuration

---

## Project Structure

```
K-Unity-Yamae/
├── kunity_yamae/                # Main Python package
│   ├── __init__.py             # Package version
│   ├── cli.py                  # CLI entry point (Click)
│   ├── config.py               # Config loader (YAML merge + env vars)
│   ├── constants.py            # Shared constants
│   ├── scanner.py              # Unity project scanner
│   ├── risk.py                 # Risk classifier (regex-based)
│   ├── modes.py                # Mode policy
│   ├── verifier.py             # Unity batchmode runner
│   ├── reporter.py             # Completion report writer
│   ├── ledger.py               # Evidence ledger (JSONL)
│   ├── context.py              # Context selector
│   ├── guards/                 # Unity-specific guards
│   │   ├── __init__.py
│   │   ├── meta_guard.py       # .meta pairing + GUID continuity
│   │   ├── yaml_guard.py       # Protected YAML file writes
│   │   ├── serialization_guard.py  # Serialized field renames
│   │   ├── boundary_guard.py   # Editor/runtime separation
│   │   ├── asmdef_guard.py     # Assembly definition graph
│   │   ├── addressables_guard.py   # Resources/Addressables paths
│   │   └── diff_guard.py       # Git diff orchestrator
│   ├── agents/                 # AI agent adapters
│   │   ├── __init__.py         # Agent registry
│   │   ├── base.py             # Base agent + system prompt
│   │   ├── codex_agent.py      # OpenAI Codex adapter
│   │   ├── claude_agent.py     # Anthropic Claude adapter
│   │   ├── gemini_agent.py     # Google Gemini adapter
│   │   ├── kimi_agent.py       # Moonshot Kimi adapter
│   │   ├── glm_agent.py        # Zhipu GLM adapter
│   │   └── mimo_agent.py       # Xiaomi MiMo adapter
│   └── rules/                  # Rule card markdown files
│       ├── global_rules.md
│       ├── serialized_field_rename.md
│       ├── meta_guid.md
│       ├── prefab_scene_yaml.md
│       ├── asmdef.md
│       ├── editor_runtime_boundary.md
│       └── resources_addressables.md
├── config/
│   └── default.yml             # Default configuration
├── Editor/
│   └── HarnessChecks.cs        # Unity Editor validation script
├── tests/                      # Test suite (14 tests)
│   ├── test_risk.py
│   ├── test_guards.py
│   └── test_scanner.py
├── docs/                       # Documentation
│   ├── ANALYSIS.md
│   ├── ARCHITECTURE.md
│   └── UPGRADE_REPORT.md
├── pyproject.toml              # Python package config
├── .gitignore
└── README.md
```

---

## Rule Cards

Rule cards are markdown files that provide Unity-specific guidance to AI agents. They are loaded and injected into agent prompts based on the task's risk triggers.

### Available Rule Cards

| Rule Card | File | When Injected |
|-----------|------|---------------|
| `unity.global` | `global_rules.md` | Always |
| `unity.serialized-field-rename` | `serialized_field_rename.md` | Field rename detected |
| `unity.meta-guid` | `meta_guid.md` | Asset move/delete detected |
| `unity.prefab-scene-yaml` | `prefab_scene_yaml.md` | YAML edit detected |
| `unity.asmdef` | `asmdef.md` | Assembly definition change |
| `unity.editor-runtime-boundary` | `editor_runtime_boundary.md` | Editor code in runtime |
| `unity.resources-addressables` | `resources_addressables.md` | Resources/Addressables change |

### Rule Card Content Example

**`serialized_field_rename.md`:**
```markdown
# unity.serialized-field-rename

**Trigger:**
- A public field in MonoBehaviour/ScriptableObject is renamed.
- A [SerializeField] or [SerializeReference] field is renamed.

**Required:**
- Add [FormerlySerializedAs("oldName")] on the new field.
- Report the old name, new name, declaring type.
- Run compile/import verification if Unity is available.

**Forbidden:**
- Do not manually rewrite scene/prefab YAML to force migration.
- Do not claim Inspector values are preserved unless a migration path exists.
```

---

## Evidence Ledger

The evidence ledger records all events during a task execution to a JSONL file.

### Event Types

| Event | Description |
|-------|-------------|
| `task_started` | Task begins with mode and risk report |
| `file_changed` | A file was modified with reason |
| `guard_result` | A guard check result |
| `verification_tier` | A verification check result |
| `manual_check` | A manual check requirement |
| `command` | A command was executed |
| `agent_output` | Agent produced output |
| `agent_error` | Agent encountered an error |
| `task_completed` | Task finished |

### Ledger File

Location: `.unity-harness/last-ledger.jsonl`

Each line is a JSON object:
```json
{"event": "task_started", "utc": "2026-06-11T12:00:00Z", "task": "Fix bug", "mode": "fast_patch", "risk_score": 15}
{"event": "file_changed", "path": "Assets/Game/DamageCalculator.cs", "reason": "null check fix"}
{"event": "guard_result", "guard": "meta_pair", "status": "pass", "details": "No issues"}
{"event": "verification_tier", "tier": "1", "name": "compile/import", "status": "passed"}
{"event": "task_completed", "status": "completed", "total_events": 5}
```

---

## Unity Editor Integration

### HarnessChecks.cs

The `Editor/HarnessChecks.cs` file provides project-specific validation that can be run via Unity's `-executeMethod` flag.

**Setup:**
1. For `kunity-yamae inspect --editor-probe --json`, no permanent copy is required; the probe is staged temporarily.
2. For custom project validation, copy `Editor/HarnessChecks.cs`, `Editor/EditorInspectionProbe.cs`, and `Editor/EditorInspectionJson.cs` to your Unity project's `Assets/Editor/` folder
3. Update the namespace to match your project
4. Configure in `.unity-harness/config.yml`:
   ```yaml
   unity:
     custom_validation_method: YourProject.Editor.HarnessChecks.RunAll
   ```

**What it checks:**
- Missing scripts in build scenes
- ScriptableObject loading validation
- Addressable key validation (stub)
- Editor inspection JSON for persistent listener targets, prefab override summaries, and missing serialized object references

**Running:**
```bash
kunity-yamae verify --custom-method YourProject.Editor.HarnessChecks.RunAll
kunity-yamae inspect --editor-probe --json
```

---

## Adding a Custom Agent

### Step 1: Create the agent file

```python
# kunity_yamae/agents/my_agent.py

import os
import time
from pathlib import Path

from .base import BaseAgent
from ..ledger import EvidenceLedger


class MyAgent(BaseAgent):
    def execute(self, task: str, project_path: Path, risk_report: dict,
                mode: str, ledger: EvidenceLedger) -> dict:
        api_key = os.environ.get(self.agent_config.get("api_key_env", "MY_API_KEY"), "")
        if not api_key:
            return {"status": "error", "message": "MY_API_KEY not set"}

        max_retries = self.agent_config.get("max_retries", 3)

        for attempt in range(max_retries):
            try:
                prompt = self._build_prompt(task, risk_report, mode, project_path)

                # Call your API here
                result_text = call_my_api(prompt, api_key)

                changes = self._parse_file_changes(result_text)
                ledger.add_event("agent_output", {
                    "agent": "my_agent",
                    "preview": result_text[:500],
                    "changes": len(changes),
                })
                return {"status": "completed", "output": result_text, "changes": changes}

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {"status": "error", "message": str(e)}

        return {"status": "error", "message": "Max retries exceeded"}
```

### Step 2: Register the agent

```python
# kunity_yamae/agents/__init__.py

from .my_agent import MyAgent

AGENT_REGISTRY = {
    # ... existing agents ...
    "my_agent": MyAgent,
}
```

### Step 3: Add configuration

```yaml
# config/default.yml

agents:
  backends:
    my_agent:
      enabled: true
      model: my-model-name
      api_key_env: MY_API_KEY
      temperature: 0.2
      max_retries: 3
```

### Step 4: Use it

```bash
kunity-yamae work "Fix bug" --agent my_agent
```

---

## Examples

### Example 1: Low-Risk Fix (Fast Patch)

```bash
$ kunity-yamae risk "Fix null check in DamageCalculator"
╭─ Risk Report ─────╮
│ Score   │ 15
│ Mode    │ fast_patch
│ Triggers│ (none)
╰───────────────────╯

$ kunity-yamae run "Fix null check in DamageCalculator" --agent mimo
K-Unity-Yamae Pipeline
Task: Fix null check in DamageCalculator

Step 1: Risk Classification
  Score: 15 | Mode: fast_patch

Step 2: Agent Execution
  Completed via mimo

Step 3: Guard Check
  No issues found

Step 4: Verification
  Tier 1: compile/import - passed

Step 5: Report
  Ledger: .unity-harness/last-ledger.jsonl
  Report: .unity-harness/reports/2026-06-11T120000Z-fix-null-check.report.md
```

### Example 2: High-Risk Rename (Migration)

```bash
$ kunity-yamae risk "Rename PlayerStats.hitpoints to health"
╭─ Risk Report ─────╮
│ Score   │ 80
│ Mode    │ migration
│ Triggers│ Serialized field/class rename
│ Rules   │ unity.serialized-field-rename
╰───────────────────╯

$ kunity-yamae run "Rename PlayerStats.hitpoints to health" --agent claude
...
Step 3: Guard Check
  [warning] serialization_rename: Field 'hitpoints' renamed to 'health'
  without [FormerlySerializedAs]. Inspector values will be lost.
...
```

### Example 3: Guard Diff

```bash
$ kunity-yamae guard-diff
╭─ Diff Guard Issues ─────╮
│ Guard          │ Severity │ Message
│ meta_pair      │ hard     │ Asset added without .meta
│ yaml_write     │ warning  │ YAML write to .prefab in migration mode
╰─────────────────────────╯
```

---

## Inspired By

- **[Gajae-Code](https://github.com/Yeachan-Heo/gajae-code)**: Interview before guessing, plan before mutation, evidence-based completion, tmux-native execution
- **[LazyCodex](https://github.com/code-yeongyu/lazycodex)**: Project memory, verified loops, hooks, model routing, skill system
- **[Unity Documentation](https://docs.unity3d.com)**: Asset metadata, serialization rules, command-line automation, Test Framework

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
git clone https://github.com/your-org/K-Unity-Yamae.git
cd K-Unity-Yamae
pip install -e ".[dev]"
pytest tests/ -v
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
