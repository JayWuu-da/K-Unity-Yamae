# K-Unity-Yamae 한국어 README

K-Unity-Yamae는 Unity 프로젝트에서 AI 코딩 에이전트가 안전하게 작업하도록 돕는 경량 하네스입니다. 핵심 역할은 위험도 분류, Unity 전용 가드레일, 검증 계획, 작업 증거 정리입니다.

## 철학

K-Unity-Yamae는 "무엇을 조심해야 하는지"와 "무엇을 검증해야 하는지"를 빠르게 정리합니다. 실제 Unity Editor 상태, Game View, 콘솔, 테스트 결과, 시각 스모크는 Unity MCP로 확인하는 것을 권장합니다.

권장 패키지:

```text
https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main
```

## 권장 검증 흐름

개발 중 빠른 확인:

```bash
python -m kunity_yamae.cli --project <UnityProject> verify --dry-run --json --qa-level minimal --live --visual-smoke
```

표준 확인:

```bash
python -m kunity_yamae.cli --project <UnityProject> verify --dry-run --json --qa-level standard --live --visual-smoke
```

릴리즈 전 확인:

```bash
python -m kunity_yamae.cli --project <UnityProject> verify --dry-run --json --qa-level release --live --visual-smoke
```

`--live`는 Unity MCP로 실행할 실제 Editor 시나리오를 출력합니다. `--visual-smoke`는 Game View 스크린샷 기반 시각 스모크 검증을 계획에 포함합니다.

## Unity MCP로 확인해야 하는 것

- `refresh_unity`: 에셋/스크립트 import와 compile 준비 상태 확인
- `run_tests`: 정확한 EditMode 또는 PlayMode 테스트 어셈블리 실행
- `manage_editor.play`: 실제 플레이 모드 진입
- `manage_camera.screenshot`: Game View 시각 스모크 캡처
- `manage_scene.get_hierarchy`: 런타임 오브젝트와 VFX 존재 확인
- `read_console`: 프로젝트 스크립트 에러와 Unity 콘솔 에러 확인
- `manage_editor.stop`: 플레이 모드 정리

## 새로 강화된 분석

- 런타임 asmdef를 기본 스캔에서도 수집합니다.
- VFX prefab을 rain, slash, aura, orbit, projectile, impact, beam 같은 의미 단위로 인덱싱합니다.
- VFX/ability 작업 context에는 spawn cap, Destroy lifetime, recursive ability guard, collider side effect, Resources.Load 경로 확인을 포함합니다.
- 테스트 어셈블리 이름을 dry-run 결과에 제안해 0개 테스트 실행 실수를 줄입니다.
- risk mode와 QA level을 분리해 개발 중에는 최소 검증, 릴리즈 전에는 강한 검증을 선택할 수 있습니다.

## 기본 원칙

K-Unity-Yamae는 Unity MCP를 대체하지 않습니다. K-Unity-Yamae는 무엇을 확인해야 하는지 정리하고, Unity MCP는 실제 Editor와 Game View에서 그 확인을 실행합니다.
