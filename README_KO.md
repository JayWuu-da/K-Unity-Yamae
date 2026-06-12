# K-Unity-Yamae 한국어 README

**K-Unity-Yamae는 Unity 프로젝트에서 AI 코딩 에이전트가 안전하게 작업하도록 돕는 경량 하네스입니다.**

Unity 프로젝트는 일반 코드 저장소보다 위험한 지점이 많습니다. `.meta` 파일의 GUID, prefab과 scene YAML, serialized field 이름, asmdef 의존성, Addressables/Resources 경로, Editor 전용 코드와 Runtime 코드의 경계가 조금만 어긋나도 겉보기에는 작은 수정이 큰 런타임 문제로 이어질 수 있습니다.

K-Unity-Yamae는 이런 위험을 자동으로 분류하고, 작업에 필요한 Unity 전용 가드레일과 검증 계획을 짧게 정리합니다. 실제 Unity Editor 실행, Play Mode, Game View, 콘솔, 스크린샷 검증은 Unity MCP와 함께 사용하는 것을 권장합니다.

---

## 목차

- [무엇을 해결하나](#무엇을-해결하나)
- [핵심 철학](#핵심-철학)
- [전체 흐름](#전체-흐름)
- [설치](#설치)
- [빠른 시작](#빠른-시작)
- [주요 명령어](#주요-명령어)
- [위험도와 작업 모드](#위험도와-작업-모드)
- [QA 레벨](#qa-레벨)
- [Unity MCP 연동 권장](#unity-mcp-연동-권장)
- [Unity 전용 가드레일](#unity-전용-가드레일)
- [VFX와 시각 스모크](#vfx와-시각-스모크)
- [컨텍스트 팩](#컨텍스트-팩)
- [데이터 검증기 생성 스킬](#데이터-검증기-생성-스킬)
- [에이전트 연동](#에이전트-연동)
- [운영 루틴](#운영-루틴)
- [한계와 주의사항](#한계와-주의사항)
- [프로젝트 구조](#프로젝트-구조)

---

## 무엇을 해결하나

K-Unity-Yamae는 AI 에이전트가 Unity 프로젝트를 수정할 때 필요한 최소한의 안전장치와 작업 판단을 제공합니다.

- Unity 프로젝트 구조, Unity 버전, package, asmdef, scene, test assembly를 스캔합니다.
- 사용자 요청과 현재 diff를 바탕으로 작업 위험도를 계산합니다.
- 위험도에 따라 필요한 rule card와 수동 확인 항목을 선택합니다.
- `.meta`, `.unity`, `.prefab`, `.asset`, `.asmdef` 같은 Unity 직렬화 파일의 변경 위험을 감지합니다.
- Unity batchmode, EditMode, PlayMode, Build validation, Unity MCP 기반 live 검증 계획을 만듭니다.
- 작업 결과를 "무엇을 했고, 무엇을 검증했고, 무엇은 아직 못 했는지"로 분리해 보고하도록 돕습니다.

이 도구의 목적은 AI 에이전트를 느리게 만드는 것이 아닙니다. 위험한 작업에는 충분한 제동을 걸고, 단순한 작업은 빠르게 통과시키는 것입니다.

---

## 핵심 철학

> 형식이 아니라 규율을 가져간다.

- **작은 C# 수정은 빠르게 처리합니다.** 오타 수정이나 국소 버그 수정에 매번 대형 계획과 장황한 인터뷰가 필요하지 않습니다.
- **Unity 직렬화 자산 변경은 엄격하게 봅니다.** prefab, scene, asset, meta, asmdef 변경은 일반 텍스트 수정과 다르게 취급해야 합니다.
- **검증은 정직해야 합니다.** Unity Editor, Play Mode, Game View를 실제로 실행하지 않았다면 실행했다고 말하지 않습니다.
- **쓰기 작업은 한 에이전트만 담당합니다.** 여러 에이전트가 동시에 읽고 분석하는 것은 괜찮지만, 같은 Unity 자산을 동시에 수정하는 것은 피합니다.
- **보고서는 희망사항이 아니라 증거를 담습니다.** 실행한 명령, 확인한 파일, 남은 위험을 분리해서 기록합니다.
- **프로젝트별 특수 사례에 갇히지 않습니다.** 특정 게임 장르나 폴더 구조에 종속되지 않고 다양한 Unity 프로젝트에 적용할 수 있어야 합니다.

---

## 전체 흐름

```text
사용자 요청
  -> Unity 프로젝트 스캔
  -> 위험도 분류
  -> 필요한 컨텍스트와 rule card 선택
  -> 에이전트 작업 또는 계획 생성
  -> Unity 전용 diff guard 확인
  -> QA 레벨에 맞는 검증 계획 생성
  -> 결과 보고서와 증거 정리
```

K-Unity-Yamae는 작업을 대신 완성하는 게임 엔진 플러그인이 아닙니다. AI 에이전트가 Unity 프로젝트를 다룰 때 "어디가 위험한지", "무엇을 확인해야 하는지", "어떤 검증을 거쳐야 말할 수 있는지"를 정리하는 하네스입니다.

---

## 설치

권장 방식은 저장소를 받아 Python 개발 모드로 설치하는 것입니다.

```bash
git clone https://github.com/JayWuu-da/K-Unity-Yamae.git
cd K-Unity-Yamae
pip install -e .
```

에이전트 연동 의존성까지 설치하려면 다음을 사용합니다.

```bash
pip install -e ".[agents]"
```

개발과 테스트까지 진행하려면 다음을 사용합니다.

```bash
pip install -e ".[dev]"
```

기본 요구사항:

- Python 3.10 이상
- Git
- Unity Editor
- Unity batchmode 검증을 사용할 경우 Unity 실행 파일 경로
- live Editor 검증을 사용할 경우 Unity MCP

---

## 빠른 시작

Unity 프로젝트를 먼저 스캔합니다.

```bash
kunity-yamae scan --project /path/to/UnityProject
```

작업 위험도를 확인합니다.

```bash
kunity-yamae risk "Rename PlayerStats.hitpoints to health"
```

AI 에이전트에 넘길 컨텍스트 팩을 생성합니다.

```bash
kunity-yamae context --project /path/to/UnityProject --pretty "Fix enemy spawn delay bug"
```

실제 수정 없이 전체 실행 계획만 확인합니다.

```bash
kunity-yamae run --project /path/to/UnityProject "Fix ShopPresenter button raycast" --plan-only --verify-dry-run --json
```

검증 계획만 빠르게 확인합니다.

```bash
python -m kunity_yamae.cli --project /path/to/UnityProject verify --dry-run --json --qa-level minimal --live --visual-smoke
```

---

## 주요 명령어

### 프로젝트 스캔

```bash
kunity-yamae scan --project /path/to/UnityProject
```

Unity 버전, package manifest, asmdef, scene, test assembly, 보호 대상 경로, VFX prefab 의미 인덱스 등을 수집합니다. 결과는 `.unity-harness/project-profile.json`에 캐시됩니다.

### 위험도 분류

```bash
kunity-yamae risk "Add a new runtime ability with projectile VFX"
```

작업 텍스트와 프로젝트 프로필을 바탕으로 0-100 사이의 위험 점수와 작업 모드를 제안합니다.

### 컨텍스트 생성

```bash
kunity-yamae context --pretty "Change UI input handling for gamepad"
```

에이전트가 읽어야 할 파일, Unity rule card, 수동 확인 항목, 런타임 안전 힌트를 묶어서 제공합니다.

### 실행 계획

```bash
kunity-yamae run "Fix player damage timing" --plan-only --verify-dry-run --json
```

실제 파일 수정 없이 어떤 단계가 필요한지 확인합니다.

### diff guard

```bash
kunity-yamae guard-diff --json
```

현재 git diff에 Unity 직렬화 위험, `.meta` 누락, asmdef 영향, Editor/Runtime 경계 위반 가능성이 있는지 확인합니다.

### 제안 패치 확인

```bash
kunity-yamae propose-edit "Fix serialized field rename" --patch-file proposed.diff --json
```

AI가 만든 unified diff를 적용하기 전에 Unity 전용 guard를 통과하는지 검사합니다.

### 검증 계획

```bash
kunity-yamae verify --dry-run --json --qa-level standard
```

현재 프로젝트 상태와 QA 레벨에 맞춰 어떤 Unity 검증을 실행해야 하는지 출력합니다.

### 공급자 상태 확인

```bash
kunity-yamae providers doctor
```

Codex, Claude, Gemini 같은 에이전트 backend 설정 상태를 점검합니다.

---

## 위험도와 작업 모드

K-Unity-Yamae는 작업을 대략 네 가지 모드로 분류합니다.

| 점수 | 모드 | 의미 |
| --- | --- | --- |
| 0-29 | fast_patch | 단순 C# 수정, 문서, 작은 설정 변경 |
| 30-59 | standard | 일반 기능 수정, 제한된 파일 변경 |
| 60-79 | asset_safe | prefab, scene, asset, import setting 등 Unity 자산 영향 |
| 80-100 | migration | serialized field/class rename, asmdef 구조 변경, 대규모 이동, 빌드 영향 |

위험도가 높다고 무조건 작업을 막는 것은 아닙니다. 대신 더 많은 rule card, 더 강한 diff guard, 더 높은 검증 레벨을 요구합니다.

---

## QA 레벨

K-Unity-Yamae는 위험도와 QA 레벨을 분리합니다. 작업 자체는 위험할 수 있어도, 현재 단계가 프로토타입인지 릴리즈 직전인지에 따라 검증 강도를 다르게 선택할 수 있습니다.

### minimal

개발 중 빠른 확인용입니다.

- 정적 guard
- Unity compile/import dry-run 계획
- 필요한 경우 제한된 EditMode 테스트
- Unity MCP live scenario 제안
- 시각 스모크 계획 포함 가능

```bash
python -m kunity_yamae.cli --project /path/to/UnityProject verify --dry-run --json --qa-level minimal --live --visual-smoke
```

### standard

기능 단위 완료 확인용입니다.

- 정적 guard
- Unity compile/import
- 관련 EditMode 테스트
- 관련 PlayMode 테스트
- Unity MCP live scenario
- Game View 시각 스모크 권장

```bash
python -m kunity_yamae.cli --project /path/to/UnityProject verify --dry-run --json --qa-level standard --live --visual-smoke
```

### release

릴리즈, 데모 제출, 병합 전 확인용입니다.

- standard 검증 전체
- build validation
- custom Editor probe
- 주요 scene smoke
- 콘솔 에러 확인
- 보고서와 증거 기록 강화

```bash
python -m kunity_yamae.cli --project /path/to/UnityProject verify --dry-run --json --qa-level release --live --visual-smoke
```

---

## Unity MCP 연동 권장

K-Unity-Yamae는 Unity MCP를 대체하지 않습니다. K-Unity-Yamae는 "무엇을 확인해야 하는지"를 계획하고, Unity MCP는 실제 Unity Editor에서 그 확인을 실행합니다.

권장 Unity MCP 패키지:

```text
https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main
```

Unity MCP로 확인하면 좋은 항목:

- `refresh_unity`: 에셋 import와 스크립트 compile 상태 확인
- `run_tests`: 정확한 EditMode 또는 PlayMode test assembly 실행
- `manage_editor.play`: 실제 Play Mode 진입
- `manage_camera.screenshot`: Game View 스크린샷 캡처
- `manage_scene.get_hierarchy`: 런타임 오브젝트, VFX, enemy, projectile, pickup 존재 확인
- `read_console`: Unity 콘솔 에러와 경고 확인
- `manage_editor.stop`: Play Mode 종료와 런타임 오브젝트 정리

권장 사용 방식:

```bash
python -m kunity_yamae.cli --project /path/to/UnityProject verify --dry-run --json --qa-level minimal --live --visual-smoke
```

이 명령은 실제 MCP를 실행하지 않고, MCP로 수행해야 할 live 검증 시나리오를 JSON으로 출력합니다. 이후 에이전트나 사용자가 Unity MCP 도구를 통해 해당 단계만 실행하면 됩니다.

---

## Unity 전용 가드레일

Unity 프로젝트에서 특히 조심해야 하는 영역을 guard로 다룹니다.

### `.meta`와 GUID

Unity는 파일 경로뿐 아니라 `.meta` GUID로 asset 참조를 유지합니다. 파일을 옮기거나 새로 만들 때 `.meta`가 누락되면 prefab, material, script reference가 깨질 수 있습니다.

### scene/prefab YAML

`.unity`, `.prefab`, `.asset` 파일은 사람이 읽을 수 있는 YAML처럼 보이지만, Unity 직렬화 규칙을 따라야 합니다. 손으로 큰 블록을 재정렬하거나 fileID를 임의로 바꾸는 변경은 위험합니다.

### serialized field rename

C# 필드 이름 변경은 Inspector에 저장된 값과 prefab override를 잃게 만들 수 있습니다. 필요한 경우 `[FormerlySerializedAs]` 같은 마이그레이션 전략을 사용해야 합니다.

### asmdef

asmdef 변경은 compile boundary, test assembly, Editor/Runtime 참조 방향에 영향을 줍니다. Runtime assembly가 Editor assembly를 참조하는 구조는 피해야 합니다.

### Resources와 Addressables

문자열 기반 경로는 컴파일러가 깨진 참조를 잡아주지 않습니다. `Resources.Load`, Addressables key, asset label 변경은 런타임 검증 계획에 포함되어야 합니다.

### Runtime과 Editor 경계

`UnityEditor` namespace는 Runtime assembly와 player build에 들어가면 안 됩니다. Editor 전용 코드는 `Editor` 폴더나 Editor assembly에 격리해야 합니다.

---

## VFX와 시각 스모크

게임 기능은 테스트가 통과해도 화면에서 안 보일 수 있습니다. 특히 VFX, UI, 카메라, shader, material, particle effect, projectile, pickup, hit effect는 시각 확인이 중요합니다.

K-Unity-Yamae는 VFX prefab을 이름과 경로 기준으로 의미 단위로 분류합니다.

- `rain`
- `slash`
- `aura`
- `orbit`
- `projectile`
- `impact`
- `beam`
- `explosion`
- `fire`
- `ice`
- `water`
- `lightning`

시각 스모크에서 확인해야 하는 것:

- Game View가 비어 있지 않은지
- 카메라가 대상 scene을 제대로 보고 있는지
- VFX 오브젝트가 생성되는지
- VFX가 너무 빨리 사라지거나 무한히 쌓이지 않는지
- collider가 의도치 않게 gameplay를 막지 않는지
- spawn cap과 lifetime 제한이 있는지
- recursive ability trigger가 무한 루프로 이어지지 않는지

K-Unity-Yamae는 이 항목을 계획과 context에 포함하고, 실제 화면 확인은 Unity MCP의 screenshot과 hierarchy 확인으로 닫는 것을 권장합니다.

---

## 컨텍스트 팩

AI 에이전트에게 전체 프로젝트를 무작정 읽히면 토큰이 낭비되고 중요한 파일이 묻힙니다. K-Unity-Yamae의 context pack은 작업에 맞는 정보만 우선순위로 묶습니다.

포함될 수 있는 정보:

- 관련 script와 assembly
- 관련 scene, prefab, material, shader 후보
- Unity package와 render pipeline 정보
- test assembly 후보
- 위험도와 선택된 rule card
- 수동 확인 항목
- 런타임 안전 체크
- VFX semantic index
- 검증 dry-run 결과

노이즈를 줄이기 위해 일반적으로 `Library`, `Temp`, `Obj`, package cache, demo sample, 외부 캐시성 산출물은 context 우선순위에서 제외합니다.

---

## 데이터 검증기 생성 스킬

`skills/unity-data-validator-builder`는 Codex가 Unity 프로젝트별 데이터 검증기 뼈대를 만들 때 쓰는 선택형 스킬입니다. K-Unity-Yamae 안에는 범용 scaffold와 절차만 두고, 실제 프로젝트별 프로필과 점검 규칙은 생성된 validator 출력 폴더의 `profiles/` 아래에 둡니다.

이 스킬은 아직 코어 `kunity-yamae` 명령으로 승격하지 않습니다. 먼저 외부 validator 산출물에서 table, reward, shop/pass, localization, payload shape, read-only server contract 비교 흐름이 반복되는지 검증한 뒤 승격 여부를 판단합니다.

---

## 에이전트 연동

K-Unity-Yamae는 특정 AI 에이전트 하나에 묶이지 않도록 설계되었습니다.

지원 또는 연동 대상:

- Codex
- Claude
- Gemini
- Kimi
- GLM
- MiMo

권장 운영 방식:

- 읽기 전용 분석은 여러 에이전트가 병렬로 수행할 수 있습니다.
- 실제 파일 수정은 한 에이전트만 담당합니다.
- Unity asset, scene, prefab을 수정할 때는 diff guard를 먼저 확인합니다.
- live Editor 검증은 Unity MCP와 연결된 한 흐름에서 수행합니다.

---

## 운영 루틴

일반적인 개발 루틴:

```bash
kunity-yamae scan --project /path/to/UnityProject
kunity-yamae context --project /path/to/UnityProject --pretty "작업 내용"
kunity-yamae run --project /path/to/UnityProject "작업 내용" --plan-only --verify-dry-run --json
```

AI 작업 후 확인 루틴:

```bash
kunity-yamae guard-diff --project /path/to/UnityProject --json
python -m kunity_yamae.cli --project /path/to/UnityProject verify --dry-run --json --qa-level minimal --live --visual-smoke
```

병합 전 루틴:

```bash
kunity-yamae guard-diff --project /path/to/UnityProject --json
python -m kunity_yamae.cli --project /path/to/UnityProject verify --dry-run --json --qa-level release --live --visual-smoke
```

---

## 한계와 주의사항

K-Unity-Yamae가 보장하지 않는 것:

- Unity Editor를 실제로 실행하지 않고 Play Mode 성공을 보장하지 않습니다.
- 스크린샷을 직접 해석해 완성된 게임 품질을 자동 판정하는 도구가 아닙니다.
- 모든 asset store package의 의미를 완벽히 이해하지 않습니다.
- 모든 shader, VFX Graph, Shader Graph, custom render feature를 자동 검증하지 않습니다.
- 손상된 scene/prefab YAML을 마법처럼 복구하지 않습니다.

따라서 다음 원칙을 지켜야 합니다.

- K-Unity-Yamae 결과는 검증 계획과 위험 신호로 사용합니다.
- 실제 Editor 상태는 Unity MCP, batchmode, 테스트, 콘솔, Game View로 확인합니다.
- 보고서에는 실행한 검증과 실행하지 못한 검증을 명확히 분리합니다.

---

## 프로젝트 구조

```text
K-Unity-Yamae/
  config/              기본 설정과 rule card
  docs/                설계 문서와 운영 문서
  Editor/              Unity Editor 통합 코드
  kunity_yamae/        Python CLI와 하네스 본체
  tests/               pytest 기반 테스트
  README.md            영어 README
  README_KO.md         한국어 README
  pyproject.toml       Python package 설정
```

---

## 정리

K-Unity-Yamae는 AI 에이전트에게 Unity 프로젝트를 맡길 때 필요한 안전벨트입니다. 핵심은 단순합니다.

- 위험한 Unity 변경을 먼저 식별합니다.
- 작업에 필요한 rule과 context만 제공합니다.
- `.meta`, prefab, scene, asmdef, serialized field를 조심스럽게 다룹니다.
- 검증을 과장하지 않고 실제 실행 여부를 분리합니다.
- Unity MCP와 함께 실제 Editor, Game View, Console까지 확인하도록 안내합니다.

작은 수정은 빠르게, 위험한 변경은 엄격하게, 검증 보고는 정직하게 처리하는 것이 K-Unity-Yamae의 목표입니다.
