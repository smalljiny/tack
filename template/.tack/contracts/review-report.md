# Contract: Review Report

- **Producer**: Claude `/flow-review` command
- **Consumers**: `/flow-done` (archive), user (review history)

## File Naming

```
.tack/local/active/<topic>/review-report-<YYMMDDHHmmss>.md
```

Timestamp format matches sibling contracts (`spec-review`, `plan-review`): 2-digit year, `YYMMDDHHmmss`.

The latest review report is determined by descending filename sort.

## Required Format

```markdown
# Review Report

- topic: <topic>
- timestamp: <YYMMDDHHmmss>
- baseBranch: <baseBranch>

## Reviewers

| reviewer | status | skipReason |
|---|---|---|
| architect (stage 1) | run \| skipped | <사유 또는 —> |
| code-reviewer | run \| skipped | — |
| security-reviewer | run \| skipped | — |
| adversarial-review | run \| skipped | <사유 또는 —> |

## Architecture Review (stage 1)
<architect 원문 출력 — 8문항 판정 + 근거 한 줄, 또는 "skipped: <skipReason>">

lock: locked \| blocked        (`topicTier == high`인 보고서에만 적고, 그 외에는 이 라인을 생략한다)

## Tier Notes
<tier 이상값·필드 부재 노트 한 줄씩, 없으면 "—">

## Code Review
<code-reviewer 원문 출력>

## Security Review
<security-reviewer 원문 출력>

## Adversarial Review
<companion stdout 원문 또는 "skipped: <skipReason>">

## 처리 내역

| issue | severity | reviewer | status |
|---|---|---|---|
| <이슈 한 줄 요약 (80자 이내)> | CRITICAL \| HIGH \| MEDIUM \| LOW | <reviewer> | fixed \| deferred |
```

## Field Definitions

### Reviewers 표

| 필드 | 값 | 설명 |
|---|---|---|
| `reviewer` | `architect (stage 1)` \| `code-reviewer` \| `security-reviewer` \| `adversarial-review` | 리뷰어 식별자 |
| `status` | `run` \| `skipped` | 실행 여부 |
| `skipReason` | 문자열 또는 `—` | skipped 시 필수; run 시 `—` |

### `## Architecture Review (stage 1)` 섹션

`topicTier == high`인 토픽에서 `/flow-review` stage 1이 산출한 architect 구조 판정을 기록한다. 섹션 본문은 architect 원문(8문항 PASS/FAIL/NOTE 판정 + 근거 한 줄)이며, 마지막 줄에 `lock` 값을 적는다.

| 필드 | 값 | 설명 |
|---|---|---|
| `lock` | `locked` \| `blocked` | 8문항 중 FAIL이 0건이면 `locked`, 1건 이상이면 `blocked`. NOTE는 lock을 막지 않는다 |

`lock: locked`는 구조 배치가 확정됐음을 뜻하며, stage 2 code-reviewer는 그 배치를 재론하지 않는다. `lock: blocked`는 stage 2가 실행되지 않았음을 뜻하며, 다음 `/flow-review` 실행이 stage 1부터 재개하는 근거가 된다.

`topicTier != high`인 토픽은 이 섹션 본문에 `skipped: topicTier not high`를 적고 `lock` 라인을 생략한다.

`topicTier == high`인 토픽의 보고서는 status가 `run`이든 `skipped`든 `lock` 라인을 항상 포함한다 — 이 라인이 다음 `/flow-review` 재진입의 재개 지점 파싱 입력이다. stage 1을 재사용해 건너뛴 실행(skipReason `stage 1 reused`)은 직전 보고서의 섹션 본문과 `lock: locked` 라인을 그대로 옮겨 적는다.

lock 값을 파일에 기록하는 주체는 `/flow-review`다 — architect의 `tools`는 확장하지 않는다.

### `## Tier Notes` 섹션

Story별 `**Risk Tier**` 필드가 없거나 값이 `low`·`normal`·`high` 중 어느 것도 아닐 때, `/flow-review`가 그 사실을 한 줄씩 기록한다. 해당 항목이 없으면 본문에 `—`를 적는다. tier 이상값 처리 규칙의 canonical 출처는 `.claude/skills/wf-risk-routing/SKILL.md`다.

### 처리 내역 표

| 필드 | 값 | 설명 |
|---|---|---|
| `issue` | 문자열 | 원문 이슈의 한 줄 요약, 80자 이내 |
| `severity` | `CRITICAL` \| `HIGH` \| `MEDIUM` \| `LOW` | 리뷰어가 분류한 severity |
| `reviewer` | 리뷰어 식별자 (`architect (stage 1)` 포함) | 이슈 출처 |
| `status` | `fixed` \| `deferred` | 처리 결과 |

severity가 명시되지 않은 이슈(adversarial-review의 설계 challenge 등)는 처리 내역 표에서 제외한다.
해당 내용은 `## Adversarial Review` 원문 섹션에서 확인한다.

## 처리 내역 산출 알고리즘

1. `/flow-review` Step 3(Transition)에서 `SAVED_SHA = git rev-parse HEAD` 캡처
2. review-fix commit 완료 후 `git log <SAVED_SHA>..HEAD --oneline` 실행
3. 신규 commit **있음** → CRITICAL·HIGH: `fixed`, MEDIUM·LOW: `deferred`
4. 신규 commit **없음** → 모든 이슈: `deferred`

## skip 사유 목록

| skipReason | 조건 | 경고 |
|---|---|---|
| `disabled` | `config.review.adversarial_enabled` 미설정 또는 `false` | 없음 (정상 opt-out) |
| `codex unavailable` | `config.codex.available=false` | 출력 |
| `codex not authenticated` | `config.codex.authenticated=false` | 출력 |
| `companion not found` | companion 스크립트 경로 해결 실패 (캐시 디렉터리 없음 또는 containment 검증 실패) | 출력 |
| `companion exited non-zero` | companion 실행 후 비-0 exit code | 출력 |
| `stage-1 blocked` | `topicTier == high`에서 stage 1 lock 판정이 `blocked` — stage 2 리뷰어와 adversarial-review가 실행되지 않음 | 출력 |
| `topicTier not high` | `topicTier ∈ {low, normal}` — stage 구분이 없어 `architect (stage 1)`이 실행되지 않음 | 없음 (정상 경로) |
| `stage 1 reused` | `review:in-progress` 재진입에서 직전 보고서의 `lock: locked`를 재사용해 stage 1을 건너뜀 | 없음 (정상 경로) |

## State Transition Responsibility

`/flow-review` Step 3(Transition)에서 `review:in-progress`로 이미 전환되므로, 보고서 작성(Step 9) 시점의 추가 상태 전환은 없다.

`review:in-progress` 상태에서 `/flow-review`를 다시 실행하는 재진입 경로는 상태 전환을 수행하지 않는다 — `review → impl` 역전이도 만들지 않는다. 재진입 시 `SAVED_SHA`는 Step 3에서 재캡처하며, 재캡처하지 않으면 이전 실행의 review-fix commit이 이번 실행의 신규 commit으로 잘못 집계된다.

## Example

```markdown
# Review Report

- topic: my-feature
- timestamp: 260417143022
- baseBranch: main

## Reviewers

| reviewer | status | skipReason |
|---|---|---|
| architect (stage 1) | skipped | topicTier not high |
| code-reviewer | run | — |
| security-reviewer | run | — |
| adversarial-review | skipped | disabled |

## Architecture Review (stage 1)
skipped: topicTier not high

## Tier Notes
—

## Code Review
**CRITICAL**: `auth.ts:42` — JWT secret이 하드코딩되어 있습니다. 환경 변수로 이동하세요.
**MEDIUM**: `utils.ts:15` — 함수명이 동작을 설명하지 않습니다.

## Security Review
**HIGH**: `api.ts:88` — 입력값 검증 없이 SQL 쿼리에 삽입됩니다.

## Adversarial Review
skipped: disabled

## 처리 내역

| issue | severity | reviewer | status |
|---|---|---|---|
| JWT secret 하드코딩 (auth.ts:42) | CRITICAL | code-reviewer | fixed |
| SQL 입력값 검증 누락 (api.ts:88) | HIGH | security-reviewer | fixed |
| 함수명 불명확 (utils.ts:15) | MEDIUM | code-reviewer | deferred |
```
