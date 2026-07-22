---
version: 6
---
# Component Boundaries: 5-tier Skill System

하네스 스킬은 prefix로 tier를 식별한다. 각 tier는 역할·호출 방식·판별 기준이 명확히 다르며, 새 스킬을 작성할 때 어느 디렉토리·이름 규칙을 따를지 결정하는 1차 기준이 된다.

## 5-tier 체계

| Tier | Prefix | 역할 | 호출 방식 | 판별 기준 |
|------|--------|------|-----------|----------|
| Orchestration | `flow-` | 워크플로우 단계 전체 소유 — 상태 머신, 시퀀싱, dev-context 전환 | 사용자 직접 (`/flow-impl`) | 사용자가 직접 시작하는 진입점인가? |
| Unit | `wf-` | 재사용 단위 작업 — 오케스트레이터·에이전트가 `Load ... and follow` | 스킬 Load 지시 | 항상 실행 가능하며 내부 전제 조건 없는가? |
| Adapter | `adapter-` | 외부 도구 래퍼 — 가용성 게이트·폴백 보유 | 오케스트레이터·다른 스킬이 Load | 외부 도구 없으면 자체적으로 skip/fallback하는가? |
| Stack | `stack-` | 기술 패턴 가이드 — capabilities 기반 발견 | skill-registry 탐색 | 기술 지식 제공인가? |
| Meta | `meta-` | 하네스 인프라 — 스킬 생성·상태 관리 | 직접 로드 (capabilities 미등록) | 하네스 자체를 관리하는가? |

`flow-*` 스킬은 frontmatter에 `user-invocable: true`를 명시한다. 플랫폼 버전별 기본값 차이를 회피하기 위한 명시적 선언이며, 슬래시 커맨드 노출의 단일 진실 원천이다.

## Tier 결정 흐름

새 스킬을 작성할 때 아래 의사결정 트리를 따른다. 첫 매칭에서 tier가 결정된다.

```
하네스 자체(스킬 생성·상태 관리·인프라)를 관리하는가?
  → 예  : meta-*  (직접 로드, capabilities 미등록)
  → 아니오
      사용자가 직접 타이핑해서 시작하는가?
        → 예  : flow-*  (user-invocable: true 명시)
        → 아니오
            외부 도구 없으면 skip/fallback을 자체 선택하는가?
              → 예  : adapter-*
              → 아니오
                  기술 스택 패턴 가이드인가?
                    → 예  : stack-*
                    → 아니오 : wf-* (단위 작업)
```

## Delegation Pattern (Standard)

스킬을 다른 스킬·에이전트·문서에서 호출할 때는 다음 한 줄 형태를 사용한다.

```
Load `.claude/skills/<name>/SKILL.md` and follow its process.
```

규칙 파일이나 contract 문서를 명시 로드할 때도 같은 형태를 사용한다.

```
Load <rule-path> and follow its process.
```

Reference cases:
- `flow-spec/SKILL.md` → `wf-brainstorming/SKILL.md`
- `flow-plan/SKILL.md` → `adapter-codex-review/SKILL.md`
- `meta-skill-creator/SKILL.md`, `agents/planner.md`, `agents/prompt-engineer.md` → `.claude/rules/common/prompt-authoring.md`

## Violation Criteria

`flow-*` 스킬이 단위 로직을 직접 정의하면 위반이다. 다음 중 하나라도 해당하면 별도 `wf-*` 또는 `adapter-*` 스킬로 추출해 위임한다.

- **이미 다른 스킬에 존재하는 로직** (duplication)
- **재사용 가능한 분리된 단위 로직**(reusable, separable unit logic)이지만 대응 스킬이 아직 없는 경우

스킬에 속해야 할 로직 예시:
- Gate 정의 (build 단계, check 시퀀스)
- 품질 기준·평가 rubric
- 산출물 형식 템플릿
- 패턴 감지·추출 로직

**체크리스트 중복 예시 (위반):**

```
# BAD: flow-* 스킬에 체크리스트 재정의
## 5. Verify quality
- [ ] Build succeeds
- [ ] Tests pass at 80%+ coverage
→ 이 체크리스트가 wf-verification/SKILL.md에 이미 정의됨

# GOOD: 스킬에 위임
Load `.claude/skills/wf-verification/SKILL.md` and run its checklist.
```

## Placement Decision Guide

새 로직을 어느 tier에 두어야 할지 결정할 때 다음 표를 참조한다.

| Need | Tier | 이유 |
|------|------|------|
| 사용자가 직접 시작하는 워크플로우 단계 | `flow-*` | 상태 머신·시퀀싱·진입점 책임 |
| 2개 이상 위치에서 재사용되는 단위 로직 | `wf-*` | 단위 작업, 내부 전제 조건 없음 |
| 외부 도구(API·CLI) 래핑 + skip/fallback | `adapter-*` | 가용성 게이트 자체 보유 |
| 특정 기술 스택의 패턴 가이드 | `stack-*` | capabilities 기반 발견 대상 |
| 하네스 인프라(스킬 생성·상태 관리) | `meta-*` | 직접 로드, capabilities 미등록 |
| 워크플로우 글루(시퀀싱·저장·트리거)이면서 사용자 진입점 아님 | flow-* 단계 내부 + 위임 | flow-* 스킬이 wf-*/adapter-*에 위임 |

## Flow Gate Pattern

복수의 유효 상태를 처리하는 `flow-*` 스킬을 작성할 때는 개별 early-stop guard를 쌓지 말고 **exhaustive 상태 테이블을 먼저 정의**한다. 이 패턴은 `wf-*`·`adapter-*` 스킬의 게이트 정의에도 동일하게 적용된다.

```
# BAD: early-stop guard 중첩
if phase != "impl": stop
if status != "in-progress": stop
if review != "done": stop

# GOOD: 상태 테이블 우선 정의
| phase:status       | Action                    |
|--------------------|---------------------------|
| impl:in-progress   | proceed                   |
| review:in-progress | show "already in review"  |
| (other)            | show gate-failure message |
```

상태 테이블은 모든 경우를 한눈에 파악하고, 신규 상태 추가 시 누락을 방지하며, 테스트 케이스 도출이 쉽다.
