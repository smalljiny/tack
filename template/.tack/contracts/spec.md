# Contract: Spec Document Format

- **Producer**: Claude brainstorming skill (content) + `/flow-spec` (persistence)
- **Consumer**: `/flow-spec` Step 7 (split analysis), Codex `spec-review` skill (quality validation), `/flow-plan` planner (delta 소비)

스펙 문서가 갖춰야 할 섹션 구조, delta·EARS·scenario 형식, PR 병합 단위 판단 기준을 정의한다.
`/flow-spec`은 브레인스토밍 호출 시 이 파일을 형식 기준으로 주입한다.

버전 정책: 섹션 구조나 분할 기준 변경 시 PR 본문에 변경점을 명시한다.
YAML frontmatter 및 version 필드는 사용하지 않는다.

---

## 스펙 문서 형식

### 필수 섹션 (모든 토픽)

```markdown
# <기능명> 스펙

**상태**: Draft
**작성일**: YYYY-MM-DD
**작성자**: @<username>

> **문서 범위**: 이 문서가 다루는 범위

## 1. 개요
### 1.1 배경
### 1.2 목적

## 2. 목표

<!-- ## 3. 은 아래 "선택 섹션"에서 토픽 유형에 맞는 것을 사용한다 -->

## 4. 의사결정

| 항목 | 결정 | 근거 |
|------|------|------|

## 5. 범위 밖 (Non-goals)

## 6. Open Questions

## 7. 관련 문서

## 8. Delta
```

### 선택 섹션 (토픽 유형에 따라 포함)

| 섹션 | Code / Feature | Workflow / Policy | Role / Structure |
|------|---------------|-------------------|-----------------|
| `## 3. 아키텍처` (전체 구조, 주요 컴포넌트) | ✅ 포함 | ⬜ 해당 없으면 생략 | ⬜ 해당 없으면 생략 |
| `## 3. 역할 정의` (역할 경계, 책임 분리) | ⬜ 해당 없으면 생략 | ✅ 포함 | ✅ 포함 |

섹션 번호 `## 3.`은 해당하는 선택 섹션에 사용한다. 토픽이 어떤 유형에도 명확히 맞지 않으면 `역할 정의` 구조를 사용해 경계와 책임을 기술한다 — `## 3.`은 항상 어떤 형태로든 필요하다.

---

## Delta 절 형식

스펙은 대상 도메인의 현재 동작 대비 변경분(delta)을 필수 섹션 `8`에 기록한다. delta는 스펙 본문과 함께 `spec:confirmed` 시점에 확정되고, `/flow-plan`의 planner가 Story 분해 입력으로 읽는다. 이 절이 delta·EARS·scenario 형식의 단일 소유처다 — 스킬·에이전트 본문은 형식을 재정의하지 않고 이 계약을 참조한다.

하위 구조는 아래 4개 서브섹션 전부를 이 순서로 포함한다. 해당 항목이 없는 서브섹션은 삭제하지 않고 본문에 `해당 없음`만 남긴다.

**domain 식별자**: `domain`은 대상 도메인 spec 파일 `docs/specs/<domain>.md`의 파일명 stem이다. 대상 spec이 아직 없는 신규 도메인은 향후 생성될 파일의 stem을 미리 정해 같은 규칙으로 표기한다. 8.2–8.4의 각 항목은 자신이 속한 domain을 접두로 명시해 8.1 표의 행과 대응시킨다.

### 8.1 Affected domains/paths

변경이 닿는 도메인과 경로 glob을 표로 열거한다. path glob은 저장소 루트 기준 상대 경로로 쓴다. 이 표는 동시 진행 토픽 간 충돌 인덱스 신호로도 쓰인다 — 두 토픽의 path glob이 겹치면 병행 작업 충돌 후보다.

| domain | path glob | baseline |
|--------|-----------|----------|
| `<domain stem>` | `<repo-root 기준 glob>` | `있음` \| `없음` |

`baseline` 열은 `docs/specs/<domain>.md`의 존재 여부이며, 아래 `## Greenfield delta와 참조 정책`의 도메인별 판정 입력이다.

### 8.2 ADDED Requirements

신규 requirement를 아래 `## EARS requirement 형식`에 따라 열거한다. 각 항목은 GIVEN/WHEN/THEN scenario를 동반한다.

항목 형식:

```
- [<domain>] <EARS requirement 한 문장>
  - GIVEN <초기 상태>
    WHEN <사건 또는 입력>
    THEN <관측 가능한 결과>
  - GIVEN <초기 상태>          # scenario가 2개 이상이면 같은 형태의 bullet을 반복한다
    WHEN <사건 또는 입력>
    THEN <관측 가능한 결과>
```

### 8.3 MODIFIED Requirements

기존 requirement의 변경을 열거한다. 대상 requirement는 그 도메인 spec(`docs/specs/<domain>.md`)의 기존 서술을 prose로 지시한다 — 안정 ID로 참조하지 않는다.

항목 형식:

```
- [<domain>] <대상 requirement를 특정하는 prose 지시> → <변경 후 EARS requirement 한 문장>
  - GIVEN <초기 상태>
    WHEN <사건 또는 입력>
    THEN <관측 가능한 결과>
```

### 8.4 REMOVED Requirements

삭제되는 requirement를 열거한다. 8.3과 동일하게 대상을 prose로 지시하고 삭제 근거를 한 줄 병기한다. 8.4 항목은 새 EARS requirement를 작성하지 않는다 — 삭제는 신규 동작을 서술하지 않기 때문이다. 대신 삭제가 반영됐음을 확인하는 scenario를 1개 갖는다.

항목 형식:

```
- [<domain>] <대상 requirement를 특정하는 prose 지시> — 삭제 근거: <한 줄>
  - GIVEN <초기 상태>
    WHEN <사건 또는 입력>
    THEN <구 동작이 더 이상 관측되지 않음>
```

---

## EARS requirement 형식

8.2 ADDED와 8.3 MODIFIED의 각 requirement는 EARS 5패턴 중 하나로 작성한다. 8.4 REMOVED는 대상 지시와 삭제 근거만 쓰므로 EARS 형식을 적용하지 않는다.

아래 표의 `<system>`은 스펙 대상 시스템의 이름으로 치환한다 — 예시의 `the service`는 자리표시자다.

| 패턴 | 형식 | 예시 |
|------|------|------|
| Ubiquitous | `the <system> shall <동작>` | the service shall reject a request without an authenticated session. |
| State | `WHILE <상태>, the <system> shall <동작>` | WHILE a batch import is running, the service shall queue incoming writes. |
| Event | `WHEN <사건>, the <system> shall <동작>` | WHEN a user confirms deletion, the service shall archive the record for 30 days. |
| Unwanted | `IF <조건>, THEN the <system> shall <동작>` | IF the upstream API returns 5xx, THEN the service shall retry up to 3 times and then surface the error. |
| Optional | `WHERE <기능 포함 시>, the <system> shall <동작>` | WHERE audit logging is enabled, the service shall record the actor id for every write. |

패턴 선택 기준: 상시 성립하는 동작은 Ubiquitous, 특정 상태가 유지되는 동안의 동작은 State(`WHILE`), 사건 발생 시점의 동작은 Event(`WHEN`), 오류·예외 조건의 대응은 Unwanted(`IF` … `THEN`), 선택 기능이 포함된 배포에서만 성립하는 동작은 Optional(`WHERE`)로 작성한다.

---

## GIVEN/WHEN/THEN scenario 형식

각 requirement는 검증 가능한 scenario를 동반한다.

```
GIVEN <초기 상태>
WHEN <사건 또는 입력>
THEN <관측 가능한 결과>
```

**세분도 규칙**: 8.2–8.4의 각 항목은 scenario를 최소 1개 갖는다. EARS Unwanted 패턴(`IF` … `THEN`)으로 작성된 requirement는 scenario를 2개 갖는다 — 조건이 성립하지 않는 정상 경로 1개와 조건이 성립하는 unwanted 경로 1개. 8.4 REMOVED 항목의 scenario는 구 동작이 더 이상 관측되지 않음을 `THEN`으로 진술한다.

**추적성 사슬**: requirement → scenario → Completion Criteria → TDD 테스트 → `/flow-verify` 게이트. scenario와 Completion Criterion의 매핑 규칙은 `.tack/contracts/implementation-plan.md`가 canonical로 소유한다 — 이 계약은 사슬의 존재만 진술한다.

---

## Greenfield delta와 참조 정책

판정은 8.1 표의 행 단위로 한다. `baseline`이 `없음`인 도메인은 그 도메인의 delta를 all-ADDED로 작성한다 — 그 도메인에 해당하는 8.3·8.4 항목을 만들지 않는다. `baseline`이 `있음`인 다른 도메인이 같은 스펙에 함께 있으면 그 도메인은 8.3·8.4를 정상적으로 사용한다. 신규 도메인을 위한 별도 문서 경로나 전용 스펙 형식은 두지 않고 동일한 delta 구조로 흡수한다.

행동 변경이 없는 토픽(문서 재배치 등)은 8.1에 접촉 경로만 기록하고 8.2–8.4를 모두 `해당 없음`으로 남긴다.

requirement 참조는 prose 지시만 사용한다 — 안정 requirement ID와 결정론적 자동병합은 도입하지 않는다. 대상 requirement가 prose 지시로 특정되지 않으면 그 requirement를 8.2 ADDED로 재작성한다. 이 경우 대상 도메인 spec의 기존 서술은 자동으로 대체되지 않으며, 병합 시점에 사람이 판단한다.

---

## 분할 판단 기준 (PR 병합 가능 단위 체크)

스펙 작성 중 아래 질문으로 단위가 PR 병합에 적합한지 점검한다. `/flow-spec` Step 7(분할 추천)도 동일 기준을 사용한다.

| 기준 | 판단 질문 |
|------|----------|
| 독립 배포 가능 | 이 스펙만 merge해도 시스템이 정상 동작하는가? |
| 독립 롤백 가능 | 이 변경만 revert해도 다른 기능이 깨지지 않는가? |
| 다른 PR에 비의존 | 동시 진행 중인 다른 PR의 완료 없이도 merge 가능한가? |
| Coupling Rationale | 여러 목표가 의존 사슬로 묶여야 한다면 §1.3에 coupling rationale을 명시했는가? |

**단위가 너무 크다는 신호**: 목표가 3개 이상이고 각각 독립 배포 가능한 경우 → 분할 권장.
**단위를 유지하는 정당한 이유**: 부분 merge 시 워크플로우가 깨지거나 이중 검증 비용이 발생하는 의존 사슬.
