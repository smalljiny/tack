# Contract: Review Report

- **Producer**: Claude `/flow-review` command
- **Consumers**: `/flow-done` (archive), user (review history)

## File Naming

```
docs/_local/active/<topic>/review-report-<YYMMDDHHmmss>.md
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
| code-reviewer | run \| skipped | — |
| security-reviewer | run \| skipped | — |
| adversarial-review | run \| skipped | <사유 또는 —> |

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
| `reviewer` | `code-reviewer` \| `security-reviewer` \| `adversarial-review` | 리뷰어 식별자 |
| `status` | `run` \| `skipped` | 실행 여부 |
| `skipReason` | 문자열 또는 `—` | skipped 시 필수; run 시 `—` |

### 처리 내역 표

| 필드 | 값 | 설명 |
|---|---|---|
| `issue` | 문자열 | 원문 이슈의 한 줄 요약, 80자 이내 |
| `severity` | `CRITICAL` \| `HIGH` \| `MEDIUM` \| `LOW` | 리뷰어가 분류한 severity |
| `reviewer` | 리뷰어 식별자 | 이슈 출처 |
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

## State Transition Responsibility

`/flow-review` Step 3(Transition)에서 `review:in-progress`로 이미 전환되므로, 보고서 작성(Step 9) 시점의 추가 상태 전환은 없다.

## Example

```markdown
# Review Report

- topic: my-feature
- timestamp: 260417143022
- baseBranch: main

## Reviewers

| reviewer | status | skipReason |
|---|---|---|
| code-reviewer | run | — |
| security-reviewer | run | — |
| adversarial-review | skipped | disabled |

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
