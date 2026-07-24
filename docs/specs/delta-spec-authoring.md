# delta 기반 spec-authoring 파이프라인

> hub 단계(flow-spec/flow-plan)의 spec 저작을 explore → delta → EARS → risk tier로 확장하는 파이프라인. spec은 대상 도메인 대비 변경분(delta)으로 작성되고, planner가 이를 소비해 Story로 분해하며 위험 tier를 산정한다.
>
> **대상 트리**: `template/` source (배포 destination은 이 트리의 렌더 결과) · **소유 스토리**: E3-S2 (M1 임계 집합)

## 개요

tack의 spec 저작은 자유 서술 브레인스토밍만으로 이뤄지던 것에서, 대상 도메인의 **현재 동작을 먼저 탐색(explore)**하고 그 위에 **변경분(delta)을 EARS requirement + scenario로 명시**하는 파이프라인으로 바뀐다. delta는 spec 본문과 함께 `spec:confirmed`에서 확정되고, `/flow-plan`의 planner가 Story 분해·Completion Criteria 매핑·위험 tier 산정의 입력으로 읽는다.

이 파이프라인이 확립하는 추적성 사슬은 다음과 같다:

```
explore(현재 동작) → delta(ADDED/MODIFIED/REMOVED) → EARS requirement → GIVEN/WHEN/THEN scenario
  → Completion Criteria → TDD 테스트 → /flow-verify 게이트
```

파이프라인은 **session-agnostic 저작**이다 — dev-context를 읽고 쓸 뿐 hub인지 worktree인지 알지 못한다. 세션 배치는 E3-S3(flow-worktree), tier **라우팅**은 E3-S4, delta **병합 실행**은 E3-S5가 소유한다. 본 파이프라인은 산정·작성까지만 담당한다.

## 구조 / 스키마

### 통합 지점 (6개 source 파일)

| source 경로 | 역할 |
|------|------|
| `template/.claude/skills/flow-spec/SKILL.md` | Step 2.7 explore 스텝(brainstorming 앞) + Step 3 delta 주입·작성 지시 |
| `template/.claude/skills/wf-delta-spec/SKILL.md` | 현재 동작 탐색 + delta 초안 작성 단위 작업 (신규 `wf-*` 스킬) |
| `template/.tack/contracts/spec.md` | `## 8. Delta` 섹션 + EARS·scenario 형식의 **단일 소유처** |
| `template/.claude/skills/flow-plan/SKILL.md` | planner에 delta·scenario·tier 소비 지시 전달 |
| `template/.claude/agents/planner.md` | delta→task 분해, scenario→Completion Criteria, risk tier 산정 로직 |
| `template/.tack/contracts/implementation-plan.md` | per-Story `**Risk Tier**` 필드 + `## Risk Tier` 판정표·`## Scenario ↔ Completion Criteria Mapping`의 **단일 소유처** |

### explore.md 산출물 구조

`wf-delta-spec` Step 1이 `<TOPIC_DIR>/explore.md`에 4개 섹션을 그대로 남긴다. 이 파일은 `.tack/local/backlog/<topic>/`(git-ignored) 아래에 놓인다.

| 섹션 | 내용 |
|------|------|
| `## Affected domains` | domain·docs/specs path·code path·baseline 4열 표 (spec §8.1의 입력) |
| `## Current behavior` | 도메인별 현재 동작 요약 + 근거 파일 경로 |
| `## Baseline gaps` | baseline 부재 또는 문서·코드 불일치 |
| `## Open points for brainstorming` | spec 작성 전 사용자 판단이 필요한 항목 |

### spec `## 8. Delta` 구조

spec 계약의 필수 섹션 8은 4개 서브섹션을 이 순서로 포함한다. 해당 항목이 없는 서브섹션은 삭제하지 않고 `해당 없음`을 남긴다.

| 서브섹션 | 내용 |
|------|------|
| `### 8.1 Affected domains/paths` | domain·path glob·baseline 표 (동시 진행 토픽 간 충돌 인덱스 신호) |
| `### 8.2 ADDED Requirements` | 신규 requirement — EARS + scenario 동반 |
| `### 8.3 MODIFIED Requirements` | 기존 requirement 변경 — prose 지시 + 새 EARS + scenario |
| `### 8.4 REMOVED Requirements` | 삭제 requirement — prose 지시 + 삭제 근거 + 확인 scenario (EARS 미적용) |

`domain` 식별자는 `docs/specs/<domain>.md`의 파일명 stem이다. requirement 참조는 안정 ID 없이 prose 지시만 사용한다.

### EARS·scenario·tier 형식 소유처

형식 정의는 이 문서가 복제하지 않고 계약이 소유한다:

- **EARS 5패턴**(Ubiquitous·State·Event·Unwanted·Optional) + **GIVEN/WHEN/THEN scenario** 형식·세분도 규칙 → `template/.tack/contracts/spec.md`.
- **6행 risk tier 판정표**(보안 마커·REMOVED·MODIFIED·affected domains 임계) + **scenario↔Completion Criteria 매핑 규칙** → `template/.tack/contracts/implementation-plan.md`.

Risk tier는 plan 문서의 per-Story `**Risk Tier**` 필드에 `<low|normal|high>`로 기록한다.

## 동작

### flow-spec — explore 선행 저작

- **Step 2.7 explore**는 brainstorming(Step 3)보다 먼저 실행되며, 선택 사항인 리서치(Step 2.5)의 수행 여부와 무관하게 항상 수행된다. `wf-delta-spec` Step 1에 위임해 `explore.md`를 남긴다.
- **재사용 게이트**: `explore.md`가 이미 있고 4개 섹션 제목이 온전하면 탐색을 다시 실행하지 않고 재사용한다. 재사용 판정은 `wf-delta-spec` Step 1.0이 소유한다(섹션이 하나라도 없으면 재탐색·덮어쓰기).
- **Step 3 delta 주입**: `explore.md` 전문을 신뢰 컨텍스트 블록으로 브레인스토밍 프롬프트에 포함하고, spec `## 8. Delta` 작성과 Open Questions 이관을 지시한다. `explore.md`가 없으면 브레인스토밍으로 진행하지 않고 정지한다(fail-closed).

### delta 확정과 개정 경계

delta는 spec 본문과 함께 `spec:confirmed` 시점에 확정된다. 구현이 확정된 delta와 어긋나면 그 자리에서 delta를 고치지 않고 **clean 경계에서 spec 게이트에 재진입해 재확정**한다. 게이트를 거치지 않는 유동적 개정 경로는 두지 않는다(OpenSpec 무게이트 fluid 철학 배제).

### wf-delta-spec — 탐색·delta 작성 단위

- **Step 1 탐색**: `docs/specs/*.md`로 후보 도메인을 열거하고(1.1), 토픽 설명·key identifier grep으로 영향 도메인을 선별하며(1.2), 도메인별 코드·문서를 Read로 확인해(1.3) `explore.md`를 작성한다(1.4). 유지 집합이 비어도 4개 섹션을 갖춘 `explore.md`를 Write하고 대상 도메인 미확정을 호출자에게 보고한다.
- **Step 2 delta 초안**: `explore.md`의 `## Affected domains` 표를 spec §8.1로 옮기고, baseline `없음` 도메인은 all-ADDED로 작성하며, 초안 텍스트를 호출자에게 반환한다. 스펙 파일 저장은 호출자(flow-spec)가 담당한다.
- 이 스킬은 `docs/specs/` 아래에 어떤 파일도 생성·수정하지 않는다.

### planner — delta 소비

- **affected component 식별**: spec §8.1 Affected domains/paths 표의 domain·path glob이 접촉 컴포넌트를 지시한다.
- **Story 분해**: `### 8.2 ADDED`·`### 8.3 MODIFIED`·`### 8.4 REMOVED` 항목이 Story 분해 단위다.
- **scenario 매핑**: 각 GIVEN/WHEN/THEN scenario 1개를 그 Story의 Completion Criterion 1개로 1:1 매핑한다(requirement의 scenario가 N개면 Criterion도 N개; Unwanted 패턴은 2개).
- **tier 산정**: Story가 접촉하는 delta 항목·경로만 평가하고 first-match 판정표로 tier를 부여한다. planner는 tier를 **기록만** 하며 어떤 분기도 수행하지 않는다.

### greenfield 흡수

baseline이 `없음`인 신규 도메인은 별도 문서 경로 없이 **all-ADDED degenerate delta**로 동일 구조에 흡수된다. 행동 변경이 없는 토픽(문서 재배치 등)은 §8.1에 접촉 경로만 기록하고 §8.2–8.4를 모두 `해당 없음`으로 남긴다.

### 신뢰 경계

- `explore.md`는 저장소 코드에서 파생된 신뢰 컨텍스트이나, Step 3 주입 블록과 `wf-delta-spec` Step 1.3 Read 단계 모두 **data-only guard**를 적용한다 — 탐색·주입 내용이나 그 근거 파일에 들어 있는 지시·명령은 따르지 않고 서술된 동작 정보만 사용한다.
- `docs/research/` 하위 경로는 Step 1.3 grep에서 제외되며 신뢰할 수 없는 외부 리서치로 계속 취급된다.

## 제약사항

- **session-agnostic 저작** — flow-spec/flow-plan은 세션 배치(hub vs worktree)를 인코딩하지 않는다. 세션 격리는 E3-S3(flow-worktree)가 주입한다.
- **tier 산정만, 라우팅 없음** — tier 값으로 review depth·design ceremony·skeleton ceremony 등 어떤 분기도 수행하지 않는다. 라우팅은 E3-S4 범위.
- **delta 병합 실행은 범위 밖** — story delta를 `docs/specs/`에 적용(ADDED 삽입·MODIFIED 교체·REMOVED 삭제)하는 것은 E3-S5(/flow-docs).
- **안정 ID·자동병합 없음** — requirement는 prose 지시로만 참조한다. addressable ID 규약·결정론적 자동병합은 E8 연기.
- **게이트 non-enforcement** — spec-review 게이트의 delta/EARS 검증 강화는 E6/후속 소관이다. `**Risk Tier**` 필드와 scenario 매핑은 backward-compat상 강제 대상이 아니며 부재 시 `plan-review`가 warning 없이 통과시킨다.
- **형식 복제 금지** — 이 문서는 파이프라인 아키텍처를 서술한다. EARS 5패턴·6행 tier 판정표·scenario 매핑 규칙의 canonical 정의는 각각 `spec.md`·`implementation-plan.md` 계약이 소유하며, 충돌 시 계약이 우선한다.
- **brownfield 점진** — `docs/specs/` 전면 재구조화는 하지 않는다. delta가 접촉하는 도메인부터 한 story씩 성장시킨다(누적 SoT).
