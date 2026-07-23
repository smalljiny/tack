---
version: 11
---
# Development Workflow

This rule extends the feature implementation workflow from git-workflow.md.

## Overall Flow

```
/flow-spec → /flow-plan → (plan-review) → /flow-impl (repeat) → /flow-review → /flow-verify → /flow-docs → /flow-pr → /flow-done
```

## Step-by-Step Rules

### 1. Write Spec (`/flow-spec`)

- Start a new topic with `/flow-spec <topic>`
- Load the brainstorming skill to write a spec draft collaboratively
- Save draft to `.tack/local/backlog/<topic>/spec.md`
- **Register topic** in `dev-context.json` at `spec:drafting` immediately after saving
- Transition to `spec:reviewing` before invoking Codex review
- Run Codex review loop until READY: `codex "spec-review 스킬로 .tack/local/backlog/<topic>/spec.md를 리뷰해줘"`
- NOT READY → rollback to `spec:drafting`, fix and re-review
- Spec is confirmed (`spec:confirmed`) when the latest `spec-review-*.md` has decision `READY` or `READY WITH NOTE`

### 2. Plan (`/flow-plan`)

- **Gate**: topic must be `spec:confirmed` — checked via `dev-context.js read --field=phase/status`
- Run with a topic argument or select from backlog list
- Moves `backlog/<topic>/` → `active/<topic>/`, updates paths in `dev-context.json`
- **planner** agent auto-activates with `.tack/local/active/<topic>/spec.md` as input
- Deliverable: `.tack/local/active/<topic>/implementation-plan.md`
- After planner completes: transition to `plan:ready`, then `plan:reviewing`
- Run Codex plan-review: `codex "plan-review 스킬을 실행해줘"`
- NOT READY → `plan:ready`, re-plan; READY → `plan:confirmed` (set by Codex plan-review)

### 3. Implement Stories (`/flow-impl`)

- **Gate**: topic must be `plan:confirmed` — blocks if not met, shows plan-review command
- Progress one Story at a time in order
- First Story: transitions to `impl:in-progress`
- 1. **tdd-specialist** auto-called → RED-GREEN-REFACTOR cycle
- 2. Immediately after implementation, **code-reviewer** auto-called → instant feedback + fixes
- 3. Commit

### 4. Final Review (`/flow-review`)

- **Gate**: topic must be `impl:in-progress` — blocks if not met
- Transitions to `review:in-progress` on start
- **code-reviewer** + **security-reviewer** run in parallel
- Quality review of full change scope

### 5. Verify (`/flow-verify`)

Must pass before completing:
- `build` — build succeeds
- `type-check` — no type errors
- `lint` — lint passes
- `test` — tests pass (80%+ coverage)
- `security` — security scan passes

### 6. Docs (`/flow-docs`)

- **Gate**: topic must be `review:in-progress` — blocks if not met
- Reconciles spec with implementation, updates existing `docs/specs/` files (or creates new ones), and commits
- On completion: transitions to `docs:generated`

### 7. PR (`/flow-pr`)

- **Gate**: topic must be `docs:generated` — blocks if not met
- Pushes the current branch to `pushRemote` and creates a GitHub Pull Request
- PR title and body come from the plan `**Commit**` field + `.tack/templates/pr-body.md`
- On completion: transitions to `pr:created`

### 8. Done (`/flow-done`)

- **Gate**: topic must be `pr:created` — blocks if not met
- Moves **all** artifacts to `.tack/local/done/<topic>/` — no deletions: spec.md, spec-review-*.md, plan-review-*.md, implementation-plan.md, review-report-*.md
- Removes topic from `dev-context.json` via `remove-topic`
- Switches `current_topic` to next active topic (or null if none remain)
- Reference document generation is handled by `/flow-docs` — `/flow-done` does not regenerate or modify `docs/specs/`

## Topic Management

```
/flow-topic                   현재 active 토픽과 backlog 목록 확인
/flow-topic switch <name>     다른 active 토픽으로 전환 (backlog 토픽은 /flow-plan 필요)
```

Topic registration happens at `/flow-spec` (not `/flow-plan`). Running `/flow-topic <name>` directly is deprecated.

## Document Lifecycle

```
스펙 초안  →  .tack/local/backlog/<topic>/spec.md        (git-ignored)
              dev-context.json: phase=spec, status=drafting
              /flow-spec 리뷰 루프 → status=reviewing → confirmed

플랜 수립  →  .tack/local/active/<topic>/                (backlog/에서 이동)
              implementation-plan.md 생성
              dev-context.json: phase=plan, status=ready → reviewing → confirmed (Codex plan-review)

구현 중    →  .tack/local/active/<topic>/                (git-ignored)
              dev-context.json: phase=impl, status=in-progress

리뷰       →  dev-context.json: phase=review, status=in-progress

문서       →  docs/specs/<confirmed-name>.md             (git-tracked, /flow-docs가 생성·갱신)
              dev-context.json: phase=docs, status=generated

PR         →  GitHub PR 생성, 브랜치 push
              dev-context.json: phase=pr, status=created

완료       →  .tack/local/done/<topic>/                  (git-ignored, 모든 산출물 보존)
              dev-context.json에서 토픽 제거 (/flow-done은 docs/specs/를 변경하지 않음)
```

## Shell Portability

macOS의 기본 셸은 **zsh**이며, bash 전용 구문은 스킬·커맨드 파일에서 에러를 유발한다.
Claude Code Bash 도구도 zsh로 실행된다.

**금지 구문:**

| 구문 | 이유 |
|------|------|
| `declare -A` (associative array) | zsh 미지원 |
| `declare -a` (indexed array) | 사용 가능하나 `typeset -a`가 portable |
| `mapfile` / `readarray` | bash 전용 builtin |

**대안:**

- 연상 배열 → 명시적 변수 (`KEY1=val1; KEY2=val2`) 또는 Node.js 스크립트 위임
- 배열 반복 → POSIX `for` 루프 + 명시적 변수 나열
- 여러 파일 복사 → 명시적 `cp` 명령어 나열

**사전 점검:** 스킬·커맨드 파일 추가·수정 시 아래 명령으로 잔존 여부 확인 권장:
```bash
grep -rnE 'declare\s+-[aA]|mapfile|readarray' .claude .tack
```

현재 코드베이스 grep 결과: 0건 (2026-04-21 기준).

**`set -u` 환경에서 빈 배열 확장:**

`set -u`(nounset)가 활성화된 셸에서 빈 배열을 `${arr[@]}`로 확장하면 "unbound variable" 에러가 발생한다.

```bash
# WRONG: set -u 환경에서 배열이 비어 있으면 에러
cmd "${arr[@]}"

# CORRECT: 배열이 비어 있을 때 안전하게 확장
cmd ${arr[@]+"${arr[@]}"}
```

이 패턴은 `arr`가 설정됐고 비어 있지 않을 때만 확장하므로, `set -u`·`set -e` 모두에서 안전하다.

## State Transition Summary

| State | Trigger |
|-------|---------|
| `spec:drafting` | `/flow-spec` registers topic |
| `spec:reviewing` | `/flow-spec` before Codex review |
| `spec:confirmed` | `/flow-spec` after READY decision |
| `plan:ready` | `/flow-plan` after planner |
| `plan:reviewing` | `/flow-plan` before Codex plan-review |
| `plan:confirmed` | Codex plan-review READY |
| `impl:in-progress` | `/flow-impl` first Story |
| `review:in-progress` | `/flow-review` on start |
| `docs:generated` | `/flow-docs` after commit |
| `pr:created` | `/flow-pr` after PR creation |
