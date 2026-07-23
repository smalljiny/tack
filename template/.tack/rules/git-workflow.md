---
version: 4
---
# Git Workflow

## Commit Message Format

```
<type>(<scope>): <description>

<optional body>
```

**Types**: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

**Scope**: 변경 범위를 나타낸다. 프로젝트별 허용 scope 목록은 `.tack/commit-scopes.md`에 정의된다.
`plan-review`는 이 목록을 warning 수준으로만 검증한다 (error 아님).

```
feat(command): add /flow-docs command
fix(rule): correct auto_commit default value
docs(harness): update workflow in CLAUDE.md
```

## 메시지 콘텐츠 정책: 워크플로우 노출 차단

**핵심 규칙**: 커밋·PR 메시지는 변경된 산출물과 그 이유만 기술한다. 메시지를 만든 하네스 워크플로우 도구(슬래시 커맨드·서브에이전트·스킬 이름)는 노출하지 않는다.

**적용 대상**:
- 신규 커밋 메시지 (plan의 `**Commit**` 필드 포함)
- PR 제목
- PR 본문의 사용자 편집 섹션

**금지 카테고리**:

| # | 카테고리 | 예시 패턴 |
|---|---------|----------|
| (a) | 슬래시 커맨드 명시 | `/flow-*`, `/dev:*`, `/harness:*`, `/graphify`, `/codex:*` |
| (b) | 워크플로우 narrative | `auto-invoked`, `RED-GREEN-REFACTOR`, `스킬 실행`, `에이전트 호출` |
| (c) | 도구 내부 상태 | `dev-context.json` 전이 narrative |
| (d) | 절차적 "via" 구문 | `via tdd-specialist`, `/flow-docs로 생성` |

**Carve-out 규칙**: 컴포넌트 이름(planner·tdd-specialist 등)·슬래시 커맨드 이름(`/flow-spec` 등)은 그 컴포넌트가 변경 대상(`scope` 또는 변경된 파일 경로)일 때만 허용한다. `feat(agent): add Write tool to planner`는 planner가 변경 대상이므로 적법, `feat(command): improve /flow-spec status display`는 `/flow-spec`(`.claude/commands/flow-spec.md` 또는 `.claude/skills/flow-spec/SKILL.md`)이 변경 대상이므로 적법, `feat: signup endpoint via planner`는 planner가 변경 대상이 아니므로 위반이다.

**Grandfathering 규칙**: 정책 병합 시점에 이미 작성된 plan `**Commit**` 필드는 위반이라도 재작성하지 않고 그대로 사용한다.

**Before/After 예시**:

(a) 슬래시 커맨드 명시 — 위반:
```
Before: feat: add signup endpoint via /flow-impl
After:  feat: add signup endpoint
```

(b) 서브에이전트 narrative — 위반:
```
Before: fix: review feedback (tdd-specialist 재실행 후 통과)
After:  fix: review feedback
```

(c) Carve-out 적법 사례 (컴포넌트가 변경 대상):
```
Before: feat(agent): add Write tool to planner
After:  feat(agent): add Write tool to planner
```
planner는 변경된 파일(`.claude/agents/planner.md`)이므로 메시지에 등장해도 적법하다.

## Commit Timing: Task Completion

`/flow-impl`이 Task를 완료하면 plan에 명시된 `**Commit**` 섹션의 메시지로 commit을 실행한다.

- **기본값**: `config.dev_impl.auto_commit = false` — Task 완료 후 사용자에게 commit 메시지와 함께 y/n/skip 프롬프트 표시
- **자동화**: `config.dev_impl.auto_commit = true` — 승인 없이 즉시 commit 실행

```bash
# auto_commit 활성화
node .tack/scripts/dev-context.js set-field \
  --field=config.dev_impl.auto_commit --value=true
```

## Review-fix Commit

`/flow-review`에서 발생한 수정은 **별도 commit으로 분리**한다.

- **amend 금지**: plan의 `**Commit**` 필드 불변성을 유지하고 review feedback 추적성을 확보한다.
- **권장 메시지 패턴** (강제 아님):
  ```
  fix: review feedback
  refactor: address review comments
  ```

## Branch Strategy

- `main` — production branch
- `develop` — integration branch
- `feature/<scope>-<description>` — feature development (기본 branchType)
- `fix/<scope>-<description>` — bug fixes
- `chore/<scope>-<description>` — configuration, dependencies, etc.

**branchType**: 기본값은 `feature`. `hotfix`/`release` 브랜치는 현재 미구현이며 별도 토픽에서 확장한다.
브랜치 패턴은 `config.git.branchPattern`으로 override 가능하다.

## PR Workflow

PR 생성은 `/flow-docs → /flow-pr → /flow-done` 순서로 진행한다:

1. **`/flow-docs`** — 구현 완료 후 참조 문서(`docs/specs/<name>.md`) 생성 + commit
2. **`/flow-pr`** — push + PR 제목·body 작성(`.tack/templates/pr-body.md` 기반) + `gh pr create` 실행
3. **`/flow-done`** — PR 생성 완료 후 artifact archive + topic 제거

**`/flow-pr` 실행 전 체크리스트:**
- [ ] working tree clean (uncommitted 변경 없음)
- [ ] `/flow-verify` 통과
- [ ] `/flow-docs` 완료 (`docs:generated` 상태)
- [ ] `config.git.{pushRemote, pullRemote, baseBranch}` 설정 확인

## git config: Remote 설정

| Config 필드 | 기본값 | 설명 |
|---|---|---|
| `config.git.pushRemote` | `origin` | 브랜치를 push할 remote |
| `config.git.pullRemote` | `origin` | base branch를 pull할 remote (fork 사용 시 `upstream`) |
| `config.git.baseBranch` | `main` | PR base branch |
| `config.git.branchPattern` | `^(feature\|fix\|chore)/` | 유효 브랜치 패턴 |

**Private Fork 설정 예시:**
```bash
node .tack/scripts/dev-context.js set-field --field=config.git.pullRemote --value=upstream
```

## Feature Implementation Workflow

```
/flow-spec → /flow-plan → /flow-impl (repeat) → /flow-review → /flow-verify → /flow-docs → /flow-pr → /flow-done
```

1. **Plan first** — planner agent로 implementation-plan.md 작성. Task별 `**Commit**` 섹션 포함.
2. **TDD approach** — tdd-specialist agent, RED-GREEN-REFACTOR, 80%+ coverage.
3. **Code review** — code-reviewer agent를 구현 직후 자동 호출.
4. **Commit per Task** — 각 Task 완료 시 plan의 `**Commit**` 메시지로 commit.
5. **Docs + PR** — `/flow-docs`로 참조 문서 확정 후 `/flow-pr`로 publish.
