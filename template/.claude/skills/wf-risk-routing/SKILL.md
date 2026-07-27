---
version: 1
name: wf-risk-routing
description: Map a plan Story's Risk Tier to its skeleton ceremony and review depth. Owns the tier routing table, the field-absent normal fallback, and the topicTier derivation. Loaded by planner, /flow-impl, and /flow-review.
origin: harness
category: dev-process
---

# wf-risk-routing

## Role and Scope

You are an orchestrator (planner, `/flow-impl`, or `/flow-review`) that has an implementation plan in hand and needs to decide how much ceremony a Story or a topic gets.

**Input**: the per-Story `**Risk Tier**` field in `.tack/local/active/<topic>/implementation-plan.md`.

**Output**: two routing decisions — 골격 의례 (skeleton ceremony, applied by planner at plan-authoring time) and 리뷰 깊이 (review depth, applied by `/flow-review`). `/flow-impl`은 이미 분해된 plan을 실행하며, tier로부터 실행 시점 분해를 유도하지 않는다.

**Out of scope**: 무엇이 어떤 tier인가의 판정. tier 판정표는 `.tack/contracts/implementation-plan.md`의 `## Risk Tier` 절이 소유하며, 이 스킬은 그 절을 인용할 뿐 판정 조건을 재정의하지 않는다.

## Tier Input Resolution

1. Story의 `**Risk Tier**` 필드 값을 읽는다 — `low` | `normal` | `high`.
2. 필드가 없는 Story는 `normal`로 간주한다. 이때 tier를 새로 산정하지 않으며 판정표를 열지 않는다 — `normal`은 tier 라우팅 도입 이전의 현행 동작과 동일하므로, 기존 plan은 이 fallback 아래에서 동작이 바뀌지 않는다. 계약이 필드 부재를 warning 없이 통과시키는 것과 일관된다.
3. 값이 `low`·`normal`·`high` 중 어느 것도 아니면 `normal`로 간주하고, 그 사실을 호출자의 산출물에 한 줄로 남긴다 — planner는 plan의 해당 Story 블록에, `/flow-impl`은 Story 브리핑에, `/flow-review`는 review-report에 남긴다.

### topicTier 유도

토픽 단위 라우팅(`/flow-review`)은 Story 단위 tier를 다음 규칙으로 집계한다.

```
topicTier = max(plan의 모든 Story의 Risk Tier)
순서: low < normal < high
```

집계 스코프는 plan의 **모든** Story다 — 완료된 Story도 포함한다. 필드 부재 Story는 위 fallback에 따라 `normal`로 계산에 들어간다.

## Routing Table

| tier | 골격 의례 (planner, plan 저작 시) | 리뷰 깊이 (`/flow-review`) |
|------|----------------------------------|----------------------------|
| `low` | 없음 | code-reviewer + security-reviewer 병렬 (현행 유지) |
| `normal` | 없음 | code-reviewer + security-reviewer 병렬 (현행 유지) |
| `high` | `Type ∈ {tdd, refactor}`인 Story에 한해 `scaffold` Story + 구현 Story로 분해. 그 외 Type은 분해하지 않는다 | stage 1 = architect 구조 판정 → lock → stage 2 = code-reviewer(변경 파일 목록 한정 unit 스코프) + security-reviewer 병렬. adversarial 리뷰 승격 + 완료 보고 직전 human gate 1회 |

라우팅은 **승격**만 정의한다. `low`·`normal`의 리뷰어 구성은 tier 라우팅 도입 이전과 동일하며, 이 표는 어떤 리뷰어도 생략하지 않는다.

`high` 행의 두 셀은 **어떤 의례가 켜지는가**만 정의한다. 각 의례의 내부 규칙은 다음 소유자에게 있다 — `scaffold` Story Type의 발동 조건과 완료 판정은 `.tack/contracts/implementation-plan.md`(`## Story Type Definitions`의 `scaffold` 행, `### scaffold 완료 판정 (언어별)` 절), stage 1 rubric·lock 판정·stage 2 스코프 산출·adversarial 실행 게이트(codex 가용성·인증 포함)·human gate 배치는 `.claude/skills/flow-review/SKILL.md`.

### 골격 의례 적용 시점

`scaffold` 분해는 plan 저작 시점(planner)에 1회 적용한다. 분해로 생성된 자식 Story(scaffold·구현 모두)는 재분해 대상이 아니다 — 자식 Story도 부모와 같은 delta를 접촉해 `high`로 유지되므로, 종료 조건 없이는 규칙이 자기 출력에 재발화한다.

`/flow-impl`은 이미 분해된 plan을 실행할 뿐 실행 시점에 Story를 분해하지 않는다. `/flow-impl`이 Story 단위 tier로 하는 일은 두 가지다.

1. `scaffold` Type Story를 만나면 계약의 `### scaffold 완료 판정 (언어별)` 절을 완료 판정 기준으로 적용한다.
2. `high` tier이면서 `Type ∈ {tdd, refactor}`인 Story에 선행 `scaffold` Story가 없으면, plan이 골격 의례를 거치지 않았다는 사실을 Story 브리핑에 한 줄로 남기고 그대로 실행한다. 실행을 중단하지 않으며 Story를 분해하지도 않는다.

## Judging Table Reference

tier 값 자체를 산정하려면 `.tack/contracts/implementation-plan.md`의 `## Risk Tier` 절을 읽는다. 그 절이 first-match 순서 규칙과 각 tier의 조건을 소유하는 단일 canonical 출처다. 이 스킬은 그 표를 축자 복제하지 않는다 — 조건이 바뀌면 계약 한 곳만 갱신되도록 하기 위함이다.

**호출 트리거**: planner가 plan 저작 중 각 Story에 `**Risk Tier**` 값을 부여할 때, Read 도구로 `.tack/contracts/implementation-plan.md`를 열어 `## Risk Tier` 절을 적용한다. plan을 소비하는 호출자(`/flow-impl`·`/flow-review`)는 기록된 값을 그대로 사용하고 계약을 열지 않는다 — 값이 없으면 위 `Tier Input Resolution` 2항의 `normal` fallback을 적용한다.

## Consumer Contract

| 호출자 | 사용하는 열 | 결정 시점 |
|--------|-------------|-----------|
| planner | 골격 의례 | plan 저작 시 Story 단위 tier로 결정 (1회) |
| `/flow-impl` | 골격 의례 결과 소비 | Story 시작 시 Story 단위 tier로 완료 판정 기준·브리핑 결정 |
| `/flow-review` | 리뷰 깊이 | 리뷰 시작 시 `topicTier`로 결정 |

세 호출자는 이 스킬을 다음 형태로 로드한다.

```
Load `.claude/skills/wf-risk-routing/SKILL.md` and follow its process.
```

## Key Principles

- **판정과 라우팅의 분리** — 무엇이 `high`인가는 계약이, `high`이면 무엇을 하는가는 이 스킬이 소유한다
- **필드 부재는 `normal`** — 실패로 처리하지 않으며 기존 plan의 동작을 바꾸지 않는다
- **승격만 정의** — `low`·`normal` 경로에서 리뷰어를 생략하지 않는다
- **골격 분해는 plan 저작 시 1회** — planner가 수행하며, 실행 시점 분해와 자식 Story 재분해는 없다
- **의례의 on/off만 소유** — 각 의례의 내부 규칙은 계약(`scaffold`)과 `/flow-review`(stage·gate)가 소유한다
