---
version: 1
---

# 시안: brownfield delta 모델을 tack story/spec 흐름에 얹기 (B1)

**상태**: 🟡 제안(시안) — 새 저장소 spec 단계에서 채택 여부 결정. dossier 확정 결정을 바꾸지 않는다.

**출처**: OpenSpec 개념·기존프로젝트 문서(adapter-exa /contents, 2026-07-22) + tack 확정 아키텍처(`glossary.md`·`session-model.md`).

## 1. 핵심 정합 — tack은 **슬롯**을 갖고 있으나 **데이터 모델**은 없다

OpenSpec의 두 앵커에 대응하는 **위치·단계**가 tack에 있지만, 그 안의 데이터 형식은 delta 병합에 부적합하다. (실검증: `docs/specs/*.md`는 prose 참조 문서 — 개요/구조/동작/제약 섹션이지 `### Requirement:` + scenario가 아니다.)

| OpenSpec | tack (확정) | 상태 |
|----------|-------------|------|
| `openspec/specs/` — source of truth(주소지정 requirements) | **`docs/specs/`** 위치·도메인 하위폴더 존재 | ⚠ **슬롯만** — 내용이 **prose**, requirements 아님 |
| archive = delta를 specs/로 **병합** | **`/flow-docs`** 병합 단계 존재 | ⚠ **슬롯만** — 현행은 **freeform prose 재조정**, 구조화 delta 적용 아님 |
| change 폴더(proposal+delta) | per-story `docs/_local/…/<story>/` | ✅ 프레이밍만 다름 |
| `/opsx:propose` / `/opsx:apply` | `/flow-spec` / `/flow-impl` | ✅ 있음 |
| **`/opsx:explore`**(변경 영역 현재 동작 매핑) | *(없음)* | 🔴 gap |
| **delta 프레이밍**(ADDED/MODIFIED/REMOVED) | story spec이 standalone freeform | 🔴 gap |

→ **정직한 규모**: 이건 "cheap 2개 gap"이 아니다. **앞단 2개 저비용 gap**(explore + delta 프레이밍) + **뒷단 1개 실질 변경**(`docs/specs/`를 주소지정 requirements로 재구조화 + `/flow-docs`를 prose-재조정 → 구조화 delta-적용으로 재작성). tack은 병합할 **자리**는 있지만 병합할 **데이터 모델**을 새로 세워야 한다.

## 2. 매핑 — 1 change = 1 story

- **`docs/specs/<domain>/`** = 누적 source of truth. brownfield 원칙: 전체 코드베이스를 미리 문서화하지 않는다. story가 건드리는 slice만 delta로 채워지며 **한 story씩 성장**.
- **story의 spec = docs/specs/에 대한 delta**. per-story spec.md를 아래 구조로:
  - **Intent/proposal** (왜) → GitHub story 이슈 본문과 연결.
  - **Delta**: `## ADDED Requirements` / `## MODIFIED Requirements` / `## REMOVED Requirements`. 각 requirement는 대상 도메인 spec을 참조하고 EARS "the <system> SHALL <응답>" 형태(B2 시너지).
  - **Affected domains/paths**: 건드리는 도메인·경로 선언 → Mongo 충돌 인덱스(G4) 급이.
- **`/flow-docs` = archive/merge**. 구현 후 story delta를 docs/specs/에 적용 — ADDED→삽입, MODIFIED→해당 requirement 교체, REMOVED→삭제. 현행 freeform "재조정"을 **구조화된 delta 적용**으로 격상. 도메인 spec이 성장·정련.

## 3. 두 gap 채우기

### G-explore: spec 단계에 Explore 하위단계 추가
hub의 spec 작성 전, 건드릴 도메인의 **현재 동작을 docs/specs/ + 코드로 매핑**한다. 도메인 spec이 없으면(첫 접촉) 탐색이 초기 baseline을 만든다. → `flow-spec`에 explore 스텝 삽입(brainstorming 전). "제안이 실제 코드에 맞게" 하는 OpenSpec의 핵심 습관.

### G-delta: story spec을 delta로 구조화
spec.md 템플릿을 §2의 ADDED/MODIFIED/REMOVED 섹션으로. greenfield는 **all-ADDED degenerate delta**(새 도메인 spec 생성)로 자연 처리 — brownfield/greenfield 단일 모델.

## 4. tack 아키텍처와의 시너지

- **greenfield = degenerate delta**: 신규 기능/도메인 → all-ADDED. 별도 greenfield 경로 불필요, 하나의 모델.
- **epic**: 여러 도메인에 걸친 story-delta 집합. 각 story가 자기 /flow-docs에서 독립 병합. epic 완료 = 전 delta 병합.
- **충돌 인덱스(G4) 날카로워짐**: delta가 "어느 도메인의 어느 requirement를 MODIFY/REMOVE"를 선언 → 병렬 두 story가 같은 도메인 spec의 같은 requirement를 건드리면 **탐지 가능한 충돌**. freeform보다 강한 신호. Mongo 충돌 인덱스와 직접 결합.
- **session-model 정합**: explore·delta 작성은 hub(spec 단계), /flow-docs 병합은 worktree→PR 경로. 기존 경계 무변경.

## 5. MVP 범위 — 프레이밍부터, 자동병합은 뒤로

**MVP = delta 프레이밍**(§3의 앞단 2개 gap: explore + ADDED/MODIFIED/REMOVED 구조). 이것만으로 (a) 변경 명확성, (b) 충돌 인덱스 신호(§4)를 얻는다. 병합은 **/flow-docs에서 에이전트·사람이 delta를 보고 적용**한다(현행 재조정과 유사, 단 delta를 입력으로).

**연기(비싼 꼬리)**: `docs/specs/`의 requirement **안정 ID** 규약 + MODIFIED/REMOVED **결정론적 자동병합** 기계장치. 이건 뒷단 실질 변경(§1)의 무거운 부분이니 **MVP에서 명시적으로 뺀다** — 아무도 무거운 버전을 먼저 만들지 않도록. docs/specs/의 requirements 재구조화는 점진적으로(delta가 건드리는 도메인부터) 가능.

## 6. ⚠ 가져오지 말 것 — OpenSpec의 "fluid, no phase gates" 철학

OpenSpec은 "fluid not rigid — no phase gates"를 표방한다. tack은 **의도적으로 phase-gated**(spec:confirmed→plan→impl, session 경계, Codex 리뷰). → **delta 아티팩트 모델만 차용하고 "무게이트 fluid" 철학은 배제**한다. tack의 게이트·리뷰 규율은 유지.

**단 iteration 단서**: delta 아티팩트는 OpenSpec의 "learn as you build" 가정을 품는다. tack은 delta를 `spec:confirmed`에서 **앞서 확정**하지만, brownfield 구현이 delta가 살짝 틀렸음을 드러내는 일이 흔하다. → 계약-타이밍 논의에서 쓴 **clean 경계 수정** 원리를 재사용: 구현이 delta와 모순되면 **clean 경계에서 delta를 개정**한다(무게이트 fluid를 들여오지 않고, 게이트 안에서 개정 경로만 허용).

## 7. Open Questions (채택 시 spec에서 확정)

- **docs/specs/ 재구조화 범위·속도**: prose → 주소지정 requirements 전환을 얼마나·언제(전면 vs delta 접촉 도메인부터 점진).
- **requirement 식별자**(자동병합 착수 시): MODIFIED/REMOVED 참조용 안정 ID/이름 규약. MVP에선 연기.
- **baseline 부트스트랩**: 도메인 첫 접촉(기존 spec 없음) — explore가 baseline 작성, delta는 all-ADDED.
- **spec-review 게이트**: Codex spec-review가 delta 정합성(docs/specs/와 모순 없는지)까지 검사하도록 확장할지.
- **EARS 결합(B2)**: delta requirement를 EARS로 쓸지(권장 — 검증 추적성).

## 8. EARS 결합 (B2) — delta requirement의 형식

**thesis**: EARS는 delta가 **operate하는 requirement 단위**를 주고, 그 scenario는 **검증 경로**를 준다. delta와 별개 아이디어가 아니라 **delta를 addressable·verifiable하게 만드는 형식**이다.

### 8.1 requirement 형식 — ID + EARS + scenario
`docs/specs/<domain>/spec.md`의 각 requirement:
```markdown
### <DOMAIN>-007: 토큰 발급          ← 안정 ID(주소지정 handle)
WHEN 사용자가 유효한 자격으로 로그인하면, the system SHALL JWT를 발급한다.   ← EARS(5패턴 중)
- GIVEN 미인증 세션, WHEN 유효 자격 제출, THEN 200 + JWT   ← acceptance scenario
```
EARS 5패턴: Ubiquitous `the … shall …` / State `WHILE …` / Event `WHEN …` / Unwanted `IF … THEN …` / Optional `WHERE …`.

### 8.2 delta는 EARS requirement를 ID로 조작
- `ADDED`: 새 ID + EARS + scenario.
- `MODIFIED <DOMAIN>-007`: 기존 ID 참조, 새 EARS/scenario 제시.
- `REMOVED <DOMAIN>-007`: 기존 ID 참조.
→ **ID가 §1·§7이 지적한 "주소지정 안정 식별자"** (Kiro FR-001 방식). MODIFIED/REMOVED 병합의 대상 위치를 ID로 특정.

### 8.3 검증 추적성 체인 (tack 기존 흐름과 결합)
```
EARS requirement(ID) → GIVEN/WHEN/THEN scenario → Completion Criteria → TDD 테스트(RED-GREEN) → verify-check
```
- scenario = tack의 **Completion Criteria**(planner가 이미 Tasks↔Criteria 1:1). → 매핑 자연스러움.
- scenario = TDD 테스트 케이스 → **tdd-specialist가 scenario에서 직접 테스트 도출** 가능.
- 결과: requirement→테스트→게이트 **end-to-end 추적성**. spec-review `quality-criterion`이 EARS 준수·scenario 커버리지를 검사.

### 8.4 MVP vs 비싼 꼬리 (§5 규율과 정합)
- **MVP**: delta requirement를 **EARS + scenario로 작성**(안정 ID 없이 prose). 이득 = 명확성·테스트성·TDD 결합 — **ID 기계장치 불필요**(사람이 delta 적용).
- **연기(full)**: 안정 ID(`<DOMAIN>-NNN`) 도입 → requirement addressable → MODIFIED/REMOVED **결정론적 병합** 가능. EARS+ID가 그 올바른 타깃 구조지만, ID 규약·자동병합은 §5대로 뒤로.
- 즉 **EARS는 MVP를 이미 개선**하고(ID 없이도), **ID는 full-병합의 enabler**다. EARS 채택이 delta 뒷단 재구조화(§1)의 방향을 정해준다 — docs/specs/를 EARS requirements로 재구조화.

### 8.5 구현 힌트
- **EARS-authoring wf-스킬**: 선행 사례 존재(`melodic-software/claude-code-plugins`의 `ears-authoring` 스킬). tack이 `wf-ears`류로 채택 가능.
- Open Q: ID 스킴(`<DOMAIN>-NNN` vs 글로벌 FR-NNN), scenario 세분도(requirement당 1+ scenario).

## 9. 요약

tack은 병합할 **자리**(source of truth `docs/specs/` + 병합 지점 `/flow-docs`)는 있으나, 그 안이 **prose라 delta 데이터 모델이 없다**. 따라서 채택 비용 = **앞단 2개 저비용 gap**(explore + delta 프레이밍) + **뒷단 1개 실질 변경**(docs/specs/ requirements 재구조화 + 병합 재작성). **MVP는 delta 프레이밍**(명확성 + 충돌 신호), 자동병합·안정ID는 연기. greenfield는 degenerate delta(all-ADDED)로 흡수, 세션 경계 무변경, delta는 clean 경계에서 개정 가능. OpenSpec의 delta 아티팩트만 차용하고 무게이트 fluid 철학은 배제.

**EARS 결합(B2, §8)**: delta requirement를 **EARS(5패턴) + GIVEN/WHEN/THEN scenario**로 쓴다. EARS는 delta가 조작할 requirement 단위를, scenario는 검증 경로를 준다 — requirement→Completion Criteria→TDD→verify-check end-to-end 추적성. 안정 ID(Kiro FR-NNN 방식)가 MODIFIED/REMOVED 주소지정을 풀지만 그건 full-병합 enabler로 연기; **EARS 자체는 ID 없이도 MVP를 개선**하고 뒷단 재구조화의 방향(docs/specs/=EARS requirements)을 정해준다.
