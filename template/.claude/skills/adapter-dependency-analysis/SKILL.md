---
version: 3
name: adapter-dependency-analysis
description: JS/TS dependency analysis workflow orchestrator. Loads stack-knip and stack-dependency-cruiser when package.json exists. Use during planning or refactoring to get a full picture of dead code and architecture violations. Skips silently if package.json is absent (non-JS/TS projects).
origin: harness
---

# adapter-dependency-analysis

JS/TS 의존성 분석 워크플로우 오케스트레이터.

> **Note**: `adapter-` 프리픽스 사용 이유 — 이 스킬은 외부 도구(`knip`, `dependency-cruiser`)
> 어댑터 스킬 두 개를 조건에 따라 로드하는 오케스트레이터다. 외부 도구가 부재하면 스킵된다는
> 어댑터 특성에 따라 5-tier 체계의 `adapter-*`로 분류한다.

## When to Activate

- `/flow-plan` 실행 시 planner 에이전트 호출 전 (자동)
- 리팩토링 계획 수립 전 프로젝트 상태 파악이 필요할 때
- 코드 품질 점검 또는 아키텍처 검증이 필요할 때

## Loading Logic

```
1. 프로젝트 루트에 package.json 존재 여부 확인
   → 존재: stack-knip + stack-dependency-cruiser 로드
   → 미존재: 스킵 (에러 없이 종료) — Python, Go 등 비JS/TS 프로젝트
```

**Non-JS/TS 프로젝트에서는 이 스킬을 무시하고 분석을 건너뛴다.**

## Workflow

### 1. 환경 확인

```bash
test -f package.json && echo "JS/TS 프로젝트" || echo "비JS/TS — 스킵"
```

### 2. 어댑터 스킬 로드 (package.json 존재 시)

두 어댑터를 함께 실행해 전체 분석을 완료한다:

**stack-knip** — 미사용 코드 탐지:
```bash
pnpm knip --reporter compact
```

**stack-dependency-cruiser** — 아키텍처 검증:
```bash
pnpm deps:check
```

### 3. 결과 해석

| 도구 | 발견 항목 | 권장 조치 |
|------|----------|----------|
| knip | 미사용 파일/export/의존성 | 플랜에서 제거 여부 판단 |
| dependency-cruiser | 순환 의존, 레이어 위반 | 플랜에 수정 Task 추가 |

### 4. 결과를 플랜에 반영

planner 에이전트에게 다음을 전달한다:
- 발견된 위반 사항
- 제거 가능한 미사용 코드 목록
- 아키텍처 규칙 위반 위치

## Extensibility

새로운 JS/TS 분석 도구 추가 시:
1. `stack-<tool>` 어댑터 스킬 신규 작성
2. 이 오케스트레이터의 "어댑터 스킬 로드" 섹션에 항목 추가

오케스트레이터가 도구별 구현 세부 사항을 모르는 구조를 유지한다.

## Scope

- **JS/TS 전용**: knip, dependency-cruiser 모두 JS/TS 생태계 도구
- **Python, Go, Java 등**: 지원하지 않음
- **도구 설치 자동화**: 이 스킬의 범위 밖 — 도구가 없으면 에러 메시지 안내

## Related Skills

- `stack-knip` — knip 어댑터 (미사용 코드 탐지 상세)
- `stack-dependency-cruiser` — dependency-cruiser 어댑터 (아키텍처 분석 상세)
