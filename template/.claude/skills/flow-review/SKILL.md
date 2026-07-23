---
version: 3
name: flow-review
description: Perform a final full code review. Runs code-reviewer and security-reviewer in parallel, then adversarial-review sequentially (opt-in).
origin: harness
user-invocable: true
---

# /flow-review

After all Stories are complete, perform a comprehensive review of the entire change scope.

## Execution Flow

### 1. Gate Check

Read `phase` and `status`:

```bash
node .tack/scripts/dev-context.js read --field=current_topic
node .tack/scripts/dev-context.js read --topic=<topic> --field=phase
node .tack/scripts/dev-context.js read --topic=<topic> --field=status
```

If `phase:status` is not `impl:in-progress`, stop immediately:

```
/flow-review를 실행할 수 없습니다.
현재 상태: <phase>:<status>
impl:in-progress 상태여야 합니다.
```

Do not warn and continue — stop entirely.

### 2. Check all Stories are complete

Read `currentStory` and the plan file:

```bash
node .tack/scripts/dev-context.js read --topic=<topic> --field=currentStory
node .tack/scripts/dev-context.js read --topic=<topic> --field=plan
```

Block if any condition is true:
- `currentStory` is not null (a Story is still in progress)
- The plan file contains any unchecked `[ ]` Story header line (`### [ ] Story N`)
- The plan file contains any unchecked `[ ]` nested Task line (`- [ ] T<storyN>.<taskM>`)

게이트 검증 명령:
```bash
grep -nE "^### \[ \]|^- \[ \] T" .tack/local/active/<topic>/implementation-plan.md
```

위 grep이 1건 이상 hit하면 차단:

```
/flow-review를 실행할 수 없습니다.
구현이 완료되지 않았습니다.
미완료 항목이 남아 있습니다: <unchecked Story·Task ID 목록>
먼저 /flow-impl로 모든 Story와 nested Task를 완료하세요.
```

### 3. Transition to `review:in-progress`

```bash
node .tack/scripts/dev-context.js update-state \
  --topic=<topic> --phase=review --status=in-progress
```

Capture the current HEAD sha for later use in Step 8 (처리 내역 산출):

```bash
SAVED_SHA=$(git rev-parse HEAD)
```

### 4. Identify Change Scope

Read the base branch from config (default: `main`):
```bash
node .tack/scripts/dev-context.js read --field=config.git.baseBranch
node .tack/scripts/dev-context.js read --field=config.git.pullRemote
```

```bash
git diff <pullRemote>/<baseBranch>...HEAD
git log <pullRemote>/<baseBranch>...HEAD --oneline
```

### 5. **Run code-reviewer + security-reviewer in parallel**

Invoke both agents simultaneously:

**code-reviewer** examines:
- Code quality across the entire change scope
- Architecture consistency
- Test coverage
- Performance considerations
- CLAUDE.md rule compliance (cross-file) — especially AskUserQuestion enforcement

**security-reviewer** examines:
- Security vulnerabilities
- Secret exposure
- Missing input validation
- Authentication/authorization issues

### 6. Consolidate and Fix Issues

**이슈 분류** (critical > high > medium > low 심각도 순):
- **CRITICAL**: Requires immediate fix. Cannot proceed before fixing.
- **HIGH**: Requires prompt fix.
- **MEDIUM**: Plan a fix.
- **LOW**: Informational — note but do not block. Suggest fixes without requiring resolution.

**수정 및 재리뷰**: Fix CRITICAL and HIGH issues, then re-review.

**Commit 규칙** — 모든 수정은 별도 commit으로 분리한다. plan의 `**Commit**` 필드를 amend하거나 덮어쓰지 않는다.

- **amend 금지**: 기존 Story commit을 수정하지 않는다.
- **권장 commit 메시지 패턴** (강제 아님):
  ```
  fix: review feedback
  refactor: address review comments
  ```
- 여러 이슈를 수정한 경우 하나의 review-fix commit으로 묶거나 이슈별로 분리 가능.
- 참조: `.tack/rules/git-workflow.md` — "Review-fix Commit" 섹션

### 7. Adversarial Review (conditional, sequential)

CRITICAL·HIGH 수정이 완료된 후 실행한다 (정제된 상태를 대상으로 해야 adversarial 피드백이 유효).

**활성화 조건** — 아래 순서로 평가하고 첫 매치만 적용 (미정의/빈값은 false로 취급):

```bash
node .tack/scripts/dev-context.js read --field=config.review.adversarial_enabled
node .tack/scripts/dev-context.js read --field=config.codex.available
node .tack/scripts/dev-context.js read --field=config.codex.authenticated
```

1. `adversarial_enabled`이 false이거나 미정의 → `skipReason="disabled"` (조용히 skip, 경고 없음)
2. `codex.available`이 false이거나 미정의 → `skipReason="codex unavailable"` (경고 출력)
3. `codex.authenticated`이 false이거나 미정의 → `skipReason="codex not authenticated"` (경고 출력)
4. 모두 true → 아래 실행 흐름 진행

활성화 방법 (기본값 false, 명시적 opt-in 필요):
```bash
node .tack/scripts/dev-context.js set-field \
  --field=config.review.adversarial_enabled --value=true
```

**조건 충족 시**:

companion 경로를 `/meta-codex-setup` one-liner 패턴으로 해결한다:

```bash
COMPANION_PATH=$(node -e "
const {existsSync,readdirSync}=require('fs');
const {join,resolve,sep}=require('path');
const {homedir}=require('os');
const base=join(homedir(),'.claude/plugins/cache/openai-codex/codex');
if(!existsSync(base)){process.exit(1);}
const vs=readdirSync(base,{withFileTypes:true})
  .filter(d=>d.isDirectory()&&/^\d+\.\d+\.\d+$/.test(d.name))
  .map(d=>d.name)
  .sort((a,b)=>{const pa=a.split('.').map(Number),pb=b.split('.').map(Number);for(let i=0;i<3;i++){if((pb[i]??0)!==(pa[i]??0))return(pb[i]??0)-(pa[i]??0);}return 0;});
if(!vs.length){process.exit(1);}
const p=join(base,vs[0],'scripts/codex-companion.mjs');
if(!resolve(p).startsWith(resolve(base)+sep)||!existsSync(p)){process.exit(1);}
process.stdout.write(p);
")
```

`<baseBranch>`는 Step 4에서 읽은 `config.git.baseBranch` (기본 `main`).

**baseBranch 형식 검증** (`flow-pr` Step 3과 동일 규약 — option injection·path traversal 차단):
- 정규식 `^[a-zA-Z0-9][a-zA-Z0-9_/.-]*$` 매칭 필수
- leading `-` 거부 (`-base` 같은 옵션 주입 차단)
- `..` 시퀀스 거부 (경로 탐색 차단)
- 검증 실패 시 경고 출력 + `adversarialStatus="skipped"`, `skipReason="invalid baseBranch"` → Step 8로 진행 (companion 호출 안 함)

companion 경로 해결 실패 시 (`COMPANION_PATH`가 빈 문자열):
- 경고 출력, `adversarialStatus="skipped"`, `skipReason="companion not found"` → Step 8로 진행

```bash
ADVERSARIAL_OUTPUT=$(node "$COMPANION_PATH" adversarial-review --wait --base "<baseBranch>")
```

- 성공(exit 0): `adversarialStatus="run"`, `ADVERSARIAL_OUTPUT`을 `## Adversarial Review` 원문으로 보관 (Step 9에서 사용)
- 비-0 exit: 경고 출력, `adversarialStatus="skipped"`, `skipReason="companion exited non-zero"` (stdout 일부를 말미에 첨부)

`adversarialStatus="run"`인 경우 Step 6과 동일한 규칙으로 CRITICAL·HIGH 이슈를 review-fix commit으로 반영한 뒤 Step 8로 진행한다. severity가 명시되지 않은 설계 challenge는 보고서 `## Adversarial Review` 원문 섹션에만 반영하고 처리 내역 표에서 제외한다.

### 8. Compute 처리 내역

review-fix commit 완료 후 실행한다.

```bash
git log <SAVED_SHA>..HEAD --oneline
```

신규 commit 존재 여부로 처리 결과를 분류한다:
- **신규 commit 있음**: CRITICAL·HIGH → `fixed`, MEDIUM·LOW → `deferred`
- **신규 commit 없음**: 모든 이슈 → `deferred`

각 이슈를 다음 형식으로 정리한다:
- `issueSummary`: 원문의 한 줄 요약, 80자 이내
- `severity`: CRITICAL | HIGH | MEDIUM | LOW
- `reviewer`: code-reviewer | security-reviewer | adversarial-review
- `status`: fixed | deferred

severity가 명시되지 않은 adversarial-review 이슈(설계 challenge 등)는 처리 내역 표에서 제외하고 `## Adversarial Review` 원문 섹션에 보존한다.

### 9. Write review-report file

파일 경로:
```
.tack/local/active/<topic>/review-report-<YYMMDDHHmmss>.md
```

`.tack/contracts/review-report.md`의 Required Format을 준수해 파일을 작성한다:

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
| adversarial-review | run \| skipped | <skipReason 또는 —> |

## Code Review
<code-reviewer 원문 출력>

## Security Review
<security-reviewer 원문 출력>

## Adversarial Review
<ADVERSARIAL_OUTPUT 원문 또는 "skipped: <skipReason>">

## 처리 내역

| issue | severity | reviewer | status |
|---|---|---|---|
| <issueSummary> | <severity> | <reviewer> | <status> |
```

### 10. Completion Report

```
Review complete

CRITICAL: 0
HIGH: 0
MEDIUM: [N]
LOW: [N]

adversarial-review: [run | skipped (<skipReason>)]
보고서: .tack/local/active/<topic>/review-report-<YYMMDDHHmmss>.md

Next: pass the verification gate with /flow-verify
```

## Next Steps

After passing review: `/flow-verify`
