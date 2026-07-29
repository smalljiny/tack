# Contract: Implementation Plan Document

- **Producer**: Claude planner agent (invoked by `/flow-plan`)
- **Consumer**: Codex `plan-review` skill (validates against spec), Claude `/flow-impl` (executes Stories)

## File Location

```
.tack/local/active/<topic>/implementation-plan.md
```

## Required Format

```markdown
# Implementation Plan: <topic name>

## Overview
[One paragraph summary of what this plan implements and why]

## Spec Reference
> Based on: `.tack/local/active/<topic>/spec.md`

## Story List

### [ ] Story 1: <title>
- **Type**: tdd | config | infra | refactor | prompt | scaffold
- **Risk Tier**: low | normal | high  (판정 근거를 괄호로 한 줄 병기 — 예: `normal (규칙 4 — MODIFIED 1건, affected domains 1개)`)
- **Goal**: [What this Story achieves — one sentence]
- **Tasks**:
  - [ ] T1.1 — <imperative subject for first task>
    - <optional sub-bullet for implementer detail>
  - [ ] T1.2 — <imperative subject for second task>
- **Completion Criteria**:
  - [ ] Verifiable criterion 1
  - [ ] Verifiable criterion 2
- **Commit**: `<type>(<scope>): <subject>`
  ```
  [optional body line 1]
  [optional body line 2]
  ```

### [ ] Story 2: <title>
...
```

## Task Line Format

각 Story 내부의 `**Tasks**:` 목록 항목은 다음 규칙을 따른다.

- **라인 형식**: `- [ ] T<storyN>.<taskM> — <subject>`
  - 예: `- [ ] T1.1 — Update version field in component files`
- **first-line subject 규칙**: 첫 줄은 한 줄 명령형 subject로 작성한다. 이 subject는 `/flow-impl`이 Story 시작 시점에 호출하는 TaskCreate의 `subject` 필드로 그대로 입력 가능해야 한다.
- **권장 길이**: subject는 80자 이내.
- **sub-bullet·코드 블록·표**: 구현자 디테일로 허용된다. 단, Claude Task 도구의 entry에는 first-line subject만 반영되며 sub-bullet은 반영되지 않는다.

## Story Type Definitions

> **Story Type ≠ Commit Type.** Story Type은 아래 6종만 허용 (`tdd|config|infra|refactor|prompt|scaffold`).
> Conventional Commits 타입(`feat|fix|docs|refactor|test|chore|perf|ci`)은 `**Commit**` 필드에서만 사용한다.
> `refactor`는 양쪽에 등장하지만 서로 다른 개념이다. 본 절은 **Story Type**의 `refactor`를 정의한다.

| Type | When to Use | Triggers |
|------|-------------|----------|
| `tdd` | 새 동작 추가 (RED-GREEN-REFACTOR) | 신규 함수·클래스·API 동작 |
| `config` | 프롬프트·문서·설정 파일 변경 (실행 코드 아님) | `.claude/`, `.codex/`, `.tack/`, `docs/`, README, spec 재배치, skill/command/rule 파일 추가·이동·병합. **단, LLM 프롬프트 본문 개선(에이전트·스킬·커맨드·규칙 프롬프트 내용 자체)은 `prompt`; `scripts/` 하위 실행 코드(`.js`/`.ts`/`.py` 등)는 `infra`·`refactor`·`tdd`** |
| `infra` | 스크립트·툴링 (비즈니스 로직 아님) | `scripts/`, CI 워크플로우, deploy 스크립트 |
| `refactor` | **실행 코드 파일 (`.ts`/`.js`/`.py` 등)** 재구조화 (테스트 커버리지 존재) | 코드 파일 재구조화. **markdown·yaml·json 변경은 `config`** |
| `prompt` | LLM 프롬프트 작성/개선 + Eval Case 평가 | 프롬프트 본문 개선 + PROPOSE→EVAL→REFINE 사이클 필요 |
| `scaffold` | 시그니처 + 타입/인터페이스 + 호출·이벤트 체인 배선 + throwing stub 작성 (함수 본문 로직 없음) | `Risk Tier == high` AND `Type ∈ {tdd, refactor}`인 Story의 분해 산물. planner가 plan 저작 시 1회만 생성한다 |

### scaffold 완료 판정 (언어별)

`scaffold` Story의 완료는 언어별 정적 검사 + entry 모듈 import 스모크로 판정한다. 이 표가 완료 판정의 canonical 출처다 — `flow-impl`·다른 스킬은 이 표를 축자 복제하지 않고 이 절을 인용한다.

| 언어 | 정적 검사 | import 스모크 |
|------|----------|--------------|
| TypeScript | `tsc --noEmit` 통과 | entry 모듈 import 성공 |
| Python | `mypy` 통과 | `import <module>` 성공 |
| JavaScript | `node --check` 통과 | dynamic `import()` 성공 |

공통 조건: 모든 미구현 함수가 throwing stub으로 배선돼 있다. 정적 검사만으로는 배선이 실제로 로드되는지 확인되지 않으므로 import 스모크를 함께 요구한다.

## Prompt Task Eval Schema

`prompt` 타입 Story의 Completion Criteria 형식. planner·plan-review·prompt-engineer가 공유하는 계약.

### 전략 선택

| 전략 식별자 | 적용 기준 | 필수 필드 |
|---|---|---|
| `direct` | 정확한 텍스트·구조 일치 | Input, Expected |
| `rubric` | 주관적 품질 (어조, 간결성, 준수 여부) | Input, Criteria, Rubric, Pass |
| `judge` | 복잡한 추론·정확성 (Claude-as-judge 별도 평가) | Input, Expected, Pass, Judge Criteria |

> 전략 태그(`[direct]`, `[rubric]`, `[judge]`)가 없으면 `direct`로 해석한다.
> Rubric은 1-5 정수 척도를 권장한다. 후속 필드가 여러 줄인 Eval Case는 4-space 들여쓰기를 사용한다.

### Eval Case 형식 예시

**`direct` 전략** (기본값 — 전략 태그 생략 가능):
```markdown
- [ ] Eval 1: Input: "<시나리오>" → Expected: "<기대 출력 텍스트 또는 패턴>"
```

**`rubric` 전략:**
```markdown
- [ ] Eval 2 [rubric]: Input: "<시나리오>"
    Criteria: "<평가 기준>"
    Rubric: "1=<나쁜 예 설명>, 5=<좋은 예 설명>"
    Pass: score >= N
```

**`judge` 전략:**
```markdown
- [ ] Eval 3 [judge]: Input: "<시나리오>"
    Expected: "<기대 동작 설명 (비교 기준용)>"
    Judge Criteria: "<judge가 평가할 항목 (예: instruction adherence, factual accuracy)>"
    Pass: judge verdict == ACCEPT
```

### Acceptance 계산 규칙

```markdown
- [ ] Acceptance: N/M eval 통과
```

- Acceptance 라인은 모든 `prompt` Story에 **필수**다. N=M인 경우에도 명시한다.
- M = Eval Case 총 개수; N = 통과 요건 개수 (기본값 N = M)
- N ≠ M이면 명시적 표기 (예: `Acceptance: 2/3 eval 통과`)
- 각 Eval의 Pass 조건이 충족되면 통과로 계산

### `prompt` 타입 전체 예시

```markdown
### [ ] Story N: <프롬프트 파일 개선>
- **Type**: prompt
- **Risk Tier**: low (규칙 6 — ADDED만, affected domains ≤ 2)
- **Goal**: ...
- **Tasks**:
  - [ ] TN.1 — <imperative subject>
- **Completion Criteria**:
  - [ ] Eval 1: Input: "..." → Expected: "..."
  - [ ] Eval 2 [rubric]: Input: "..."
      Criteria: "..."
      Rubric: "1=..., 5=..."
      Pass: score >= 4
  - [ ] Acceptance: 2/2 eval 통과   ← 필수 (N=M인 경우도 명시)
- **Commit**: `feat(agent): ...`
```

## Completion Marker

When a Story is complete, its checkbox is updated:
```
### [ ] Story N  →  ### [x] Story N
```

## Commit Section

Each Story includes a `**Commit**` field describing the commit to create when the Story is complete.

**Format:**
```
- **Commit**: `<type>(<scope>): <subject>`
```

Optional multi-line body (indented under the backtick line):
```
- **Commit**: `feat(command): add /flow-docs command`
  ```
  Separates reference doc generation from /flow-done.
  Entry gate: review:in-progress. Completion: docs:generated.
  ```
```

**Validation** (performed by `plan-review`, warning level only — not blocking):
- `type` must be one of: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `ci`
- `scope` should match an entry in `.tack/commit-scopes.md` (free-form also accepted)
- `subject` must be 72 characters or fewer
- Scope parser regex: `^\|\s*([a-z0-9_-]+)\s*\|` (first column of the Markdown table, excluding `scope` header and separator rows)

**Backward compatibility**: Plans written before the `pr-driven-commit-workflow` topic's Task 4 do not require a `**Commit**` field. `plan-review` skips Commit validation when the field is absent — it is treated as a warning, not a failure.

## Risk Tier

각 Story는 접촉하는 spec `## 8. Delta` 항목·경로의 형태로 위험 tier를 산정한다. 이 절이 tier 판정표의 단일 canonical 출처다 — planner·다른 스킬은 이 표를 축자 복제하지 않고 이 절을 인용한다.

first-match 순서 규칙. Story 단위로 그 Story가 접촉하는 delta 항목·경로만 평가한다. 위에서부터 첫 매칭에서 tier가 결정된다.

| 우선순위 | 조건 (위에서부터 첫 매칭) | Tier |
|---|---|---|
| 1 | Affected domains/paths가 보안·자격증명 마커를 포함 (`auth`, `login`, `session`, `token`, `secret`, `credential`, `permission`, `role`, `crypto`, `payment`, `deploy`) | high |
| 2 | REMOVED requirement ≥ 1 | high |
| 3 | MODIFIED requirement ≥ 3 | high |
| 4 | MODIFIED requirement 1–2 (REMOVED 0) | normal |
| 5 | Affected domains ≥ 3 (ADDED만이어도) | normal |
| 6 | 그 외 (ADDED만 + affected domains ≤ 2) | low |

tier는 plan 문서의 per-Story `**Risk Tier**` 필드에 **기록만** 한다. 이 계약은 tier 값에 따른 어떤 분기도 정의하지 않는다 — 리뷰 깊이·design ceremony·골격 의례 라우팅은 이 계약의 범위 밖이다. 그 라우팅의 소유자는 `.claude/skills/wf-risk-routing/SKILL.md`이며, tier 값을 읽어 골격 의례와 리뷰 깊이를 결정하는 주체는 그 스킬과 그 스킬을 로드하는 planner·`/flow-impl`·`/flow-review`다. `## Story Type Definitions`의 `scaffold` 행이 기술하는 것은 그 Story Type의 발동 조건이며, 라우팅 실행 규칙은 아니다.

**Backward compatibility**: `**Risk Tier**` 필드가 없는 plan은 실패로 처리하지 않는다. `plan-review`는 필드 부재를 warning 없이 통과시킨다 — 필드는 기대값이며 강제 대상이 아니다.

## Scenario ↔ Completion Criteria Mapping

spec `## 8. Delta`의 각 GIVEN/WHEN/THEN scenario 1개는 그 Story의 Completion Criterion 1개로 1:1 매핑된다. 이 절이 매핑 규칙의 canonical 출처다.

- delta requirement의 scenario가 N개면 대응 Story는 그 requirement에 대해 Completion Criterion을 N개 갖는다.
- EARS Unwanted 패턴(`IF … THEN`) requirement는 정상 경로·unwanted 경로 scenario 2개를 가지므로 Completion Criterion도 2개로 매핑된다.
- scenario 형식과 최소 개수 규칙은 `.tack/contracts/spec.md`가 소유한다 — 이 절은 매핑 관계만 정의한다.

## Key Constraints

- Each Story must be independently executable and committable
  - **`scaffold` carve-out**: `scaffold` Story는 독립 실행·커밋 가능 기준은 충족하되, **독립 배포 가능** 기준은 동일 PR 내 후속 구현 Story와 묶인 PR 단위에서 평가한다
- Completion Criteria must be verifiable (runnable command, observable output, or checkable file)
- Story ordering must respect dependency relationships
- Stories must not implement anything outside the spec scope
- `**Commit**` field is expected (not enforced) for plans written after the `pr-driven-commit-workflow` topic's Task 4; `plan-review` validates it at warning level only
