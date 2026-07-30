---
version: 6
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
python3 .tack/scripts/dev_context.py set-field \
  --field=config.dev_impl.auto_commit --value=true
```

`config.dev_impl.auto_commit`은 `local` layer이므로 git-ignored `.tack/local/dev-context.json`에 기록된다 — 커밋되지 않으며 이 머신에만 적용된다. 무인 실행 선호는 개인 설정이라 `--layer=shared`로 공유 층에 승격하려 하면 `set-field`가 거부한다.

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

| Config 필드 | 기본값 | 저장 층 | 저장 파일 | 설명 |
|---|---|---|---|---|
| `config.git.pushRemote` | `origin` | `shared` | `.tack/config.json` (tracked) | 브랜치를 push할 remote |
| `config.git.pullRemote` | `origin` | `shared` | `.tack/config.json` (tracked) — 확정값이 `upstream`이면 개인 층 | base branch를 pull할 remote (fork 사용 시 `upstream`) |
| `config.git.baseBranch` | `main` | `shared` | `.tack/config.json` (tracked) | PR base branch |
| `config.git.branchPattern` | `^(feature\|fix\|chore)/` | `shared` | `.tack/config.json` (tracked) | 유효 브랜치 패턴 |

네 키 모두 `shared` layer이므로 기본 라우팅(플래그 없음)에서 `set-field`가 tracked `.tack/config.json`에 기록한다 — 커밋 대상이며 팀 전체가 공유한다. 예외는 `pullRemote` 하나다: `/flow-setup git`은 확정값이 `upstream`일 때 그 키만 `--layer=local`로 개인 층에 기록한다.

**Private Fork 설정 예시:**
```bash
python3 .tack/scripts/dev_context.py set-field --field=config.git.pullRemote --layer=local --value=upstream
```

`--layer=local`을 붙여 git-ignored `.tack/local/dev-context.json`에 기록한다. fork를 쓰는 것은 그 사용자의 사정이므로 공유 층을 오염시키지 않는다 — tracked 파일에 `upstream`이 들어가면 fork를 쓰지 않는 팀원이 그 값을 상속해 PR diff 기준이 어긋난다. `read`는 local을 먼저 보므로 이 개인 값이 팀 값을 가린다. `/flow-setup git` 재실행은 `pushRemote`·`baseBranch`·`branchPattern`의 공유 층만 갱신하지만 `pullRemote`은 예외다 — 확정값이 `upstream`이면 그 스킬이 개인 층에 직접 쓰므로 이 값이 갱신된다.

## Feature Implementation Workflow

```
/flow-spec → /flow-plan → /flow-impl (repeat) → /flow-review → /flow-verify → /flow-docs → /flow-pr → /flow-done
```

1. **Plan first** — planner agent로 implementation-plan.md 작성. Task별 `**Commit**` 섹션 포함.
2. **TDD approach** — tdd-specialist agent, RED-GREEN-REFACTOR, 80%+ coverage.
3. **Code review** — code-reviewer agent를 구현 직후 자동 호출.
4. **Commit per Task** — 각 Task 완료 시 plan의 `**Commit**` 메시지로 commit.
5. **Docs + PR** — `/flow-docs`로 참조 문서 확정 후 `/flow-pr`로 publish.
