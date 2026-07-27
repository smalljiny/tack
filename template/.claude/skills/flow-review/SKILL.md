---
version: 9
name: flow-review
description: Perform a final full code review. On high-tier topics, runs a stage-1 architect structural verdict that locks the layout before stage-2 code-reviewer and security-reviewer, auto-promotes adversarial review, and gates completion on user approval; otherwise runs both reviewers in parallel with adversarial review opt-in.
origin: harness
user-invocable: true
---

# /flow-review

After all Stories are complete, perform a comprehensive review of the entire change scope.

## Execution Flow

### 1. Gate Check

Read `phase` and `status`:

```bash
python3 .tack/scripts/dev_context.py read --field=current_topic
python3 .tack/scripts/dev_context.py read --topic=<topic> --field=phase
python3 .tack/scripts/dev_context.py read --topic=<topic> --field=status
```

`phase:status`를 아래 상태 테이블과 대조한다. 이 표는 exhaustive하다 — 열거되지 않은 모든 상태는 `(그 외)` 행으로 처리한다.

| `phase:status` | 동작 |
|----------------|------|
| `impl:in-progress` | 첫 진입. Step 2로 진행하고, Step 3에서 `review:in-progress`로 전환한다 |
| `review:in-progress` | 재진입. 상태 전환 없이 Step 2로 진행하고, Step 3에서 `SAVED_SHA`만 재캡처한다. 재개 지점은 Step 4.5가 결정한다 |
| (그 외) | 아래 메시지를 출력하고 정지 |

`(그 외)` 행의 게이트 실패 메시지:

```
/flow-review를 실행할 수 없습니다.
현재 상태: <phase>:<status>
impl:in-progress 또는 review:in-progress 상태여야 합니다.
```

경고 후 계속하지 않는다 — 완전히 정지한다.

### 2. Check all Stories are complete

Read `currentStory` and the plan file:

```bash
python3 .tack/scripts/dev_context.py read --topic=<topic> --field=currentStory
python3 .tack/scripts/dev_context.py read --topic=<topic> --field=plan
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

### 3. Transition to `review:in-progress` and capture `SAVED_SHA`

Step 1 상태 테이블이 정한 경로에 따른다.

**`impl:in-progress` 경로 (첫 진입)** — 상태를 전환한다:

```bash
python3 .tack/scripts/dev_context.py update-state \
  --topic=<topic> --phase=review --status=in-progress
```

**`review:in-progress` 경로 (재진입)** — 상태 전환을 실행하지 않는다. `review → impl` 역전이도 만들지 않는다.

두 경로 모두 현재 HEAD sha를 캡처한다. Step 8(처리 내역 산출)의 입력이며, 재진입 시 재캡처하지 않으면 이전 실행의 review-fix commit이 이번 실행의 신규 commit으로 잘못 집계된다:

```bash
SAVED_SHA=$(git rev-parse HEAD)
```

### 4. Identify Change Scope

Read the base branch from config (default: `main`):
```bash
python3 .tack/scripts/dev_context.py read --field=config.git.baseBranch
python3 .tack/scripts/dev_context.py read --field=config.git.pullRemote
```

```bash
git diff <pullRemote>/<baseBranch>...HEAD
git log <pullRemote>/<baseBranch>...HEAD --oneline
```

**호출 트리거**: stage 2의 code-reviewer 스코프로 넘길 변경 파일 경로 목록을 여기서 산출한다. Bash 도구로 다음을 실행하고 결과를 `CHANGED_FILES`로 보관한다:

```bash
git diff --name-only <pullRemote>/<baseBranch>...HEAD
```

### 4.5. Compute `topicTier` and resume point

plan 파일의 Story별 `**Risk Tier**` 필드를 읽어 토픽 단위 tier를 산출한다.

`topicTier` 유도 규칙(`max` 집계, `low < normal < high` 순서, 필드 부재 Story 처리, 이상값 처리)의 canonical 출처는 라우팅 소유자다. 아래 스킬을 로드해 그 규칙으로 `topicTier`를 산출하고, 산출된 tier가 어떤 리뷰 깊이에 매핑되는지도 같은 스킬에서 읽는다:

Load `.claude/skills/wf-risk-routing/SKILL.md` and follow its process.

tier 값이 `low`·`normal`·`high` 중 어느 것도 아닌 Story가 있으면 그 스킬의 이상값 규칙에 따라 `normal`로 계산하고, 그 사실을 Step 9에서 review-report `## Tier Notes` 섹션에 한 줄로 남긴다.

**재개 지점 결정** (Step 1에서 `review:in-progress` 재진입으로 판정된 경우에만 적용):

**호출 트리거**: Glob 도구로 `.tack/local/active/<topic>/review-report-*.md`를 열거하고, 파일명 내림차순 정렬로 최신 1개를 Read한다. 그 파일의 `## Architecture Review (stage 1)` 섹션 `lock` 값으로 재개 지점을 정한다.

아래 표는 위에서부터 첫 매칭으로 적용하며 exhaustive하다.

| 조건 (위에서부터 첫 매칭) | 재개 지점 |
|---------------------------|-----------|
| `topicTier != high` | Step 5부터 (stage 구분 없는 현행 병렬 리뷰) |
| `review-report-*.md` 파일 없음 | Step 5부터 |
| `lock: locked` | Step 5 stage 2부터 (stage 1 재실행 없음, 이전 lock 판정 재사용) |
| `lock: blocked` | Step 5 stage 1부터 |
| `lock` 값 파싱 실패 (`## Architecture Review (stage 1)` 섹션 부재 또는 `lock:` 라인 부재) | Step 5 stage 1부터 |

마지막 행은 harness 업그레이드 이전 형식(`## Architecture Review (stage 1)` 섹션이 없는 보고서)으로 남은 토픽을 흡수한다.

`lock: locked` 행으로 재개해 stage 1을 건너뛴 실행은, Step 9에서 `architect (stage 1)` 행을 `skipped` / skipReason `stage 1 reused`로 적고 **이전 보고서의 `## Architecture Review (stage 1)` 섹션 본문과 `lock: locked` 라인을 그대로 옮겨 적는다**. lock 라인은 다음 재진입의 파싱 입력이므로 `high` 토픽 보고서에서 생략하지 않는다.

`impl:in-progress` 첫 진입은 항상 Step 5부터 시작한다.

### 5. **Run reviewers**

`topicTier` 값으로 두 경로 중 하나를 택한다.

#### 5-A. `topicTier ∈ {low, normal}` — 현행 병렬 리뷰 (변경 없음)

code-reviewer와 security-reviewer를 동시에 호출한다. stage 구분·lock 판정·human gate는 적용하지 않는다.

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

이 경로를 마치면 Step 6으로 진행한다.

#### 5-B. `topicTier == high` — stage 1 → lock → stage 2

**stage 1 — architect 단독 호출 (구조 판정)**

architect 에이전트를 단독으로 호출한다. code-reviewer·security-reviewer는 이 시점에 호출하지 않는다. architect에게 변경 범위(Step 4의 `git diff` 결과)와 아래 8문항 rubric을 전달한다.

| # | 문항 |
|---|------|
| 1 | 변경이 맞는 위치에 있는가 |
| 2 | 추상 수준이 주변 코드와 맞는가 |
| 3 | 애초에 해야 할 일인가 |
| 4 | 같은 일을 하는 것이 이미 있는가 |
| 5 | 기존 패턴과 일관적인가 |
| 6 | 호출·이벤트 체인이 완결됐는가 |
| 7 | `.claude/rules/common/component-boundaries.md`의 5-tier 배치가 맞는가 |
| 8 | 스킬·규칙 호출이 Delegation Pattern 표준 형태를 쓰는가 |

각 문항의 판정은 PASS / FAIL / NOTE 셋 중 하나다. architect는 문항별 판정 + 근거 한 줄과 마지막 `lock:` 라인을 출력한다.

**lock 판정**: 8문항 중 FAIL 판정이 **1건 이상**이면 `lock: blocked`, FAIL이 **0건**이면 `lock: locked`. advisory NOTE는 lock을 막지 않는다.

**`lock == locked`** → stage 2로 진행한다.

**`lock == blocked`** → stage 2를 실행하지 않는다. 정지하기 **전에** Step 9의 형식으로 stage-1-only review-report를 작성한다 — Reviewers 표는 `architect (stage 1)` = `run`, `code-reviewer`·`security-reviewer`·`adversarial-review` = `skipped` (skipReason `stage-1 blocked`). 이 파일이 다음 실행의 재개 지점 입력이며, 보류 상태에서도 stage-1 원문과 lock 값이 보존돼 재실행 비용이 줄어든다.

이 경로에서는 Step 6·7·8이 실행되지 않으므로 나머지 섹션은 다음과 같이 채운다: `## Tier Notes`는 Step 4.5에서 산출한 노트를 그대로 적고 노트가 없으면 `—`를 적는다, `## Code Review`·`## Security Review`·`## Adversarial Review` 본문은 각각 `skipped: stage-1 blocked`, `## 처리 내역` 표는 stage-1 FAIL 문항을 `reviewer` = `architect (stage 1)`, `severity` = `HIGH`, `status` = `deferred`로 채운다.

보고서를 쓴 뒤 다음을 출력하고 정지한다:

```
stage 1 구조 판정 결과: blocked
FAIL 문항: <문항 번호 목록>
보고서: .tack/local/active/<topic>/review-report-<YYMMDDHHmmss>.md

구조 수정을 review-fix commit으로 반영한 뒤 /flow-review를 다시 실행하세요.
stage 1부터 재실행됩니다.

수정에 plan Story 추가가 필요하면 Step 2 완료 게이트에 걸리므로,
먼저 phase를 impl로 되돌린 뒤 /flow-impl로 신규 Story를 실행하세요:
  python3 .tack/scripts/dev_context.py update-state \
    --topic=<topic> --phase=impl --status=in-progress
```

토픽 상태는 `review:in-progress`로 유지한다. `/flow-review` 자신은 `review → impl` 역전이를 만들지 않는다 — 위 rollback은 사용자가 명시적으로 실행하는 경로다.

**stage 2 — code-reviewer(unit) + security-reviewer 병렬**

`lock == locked`일 때만 실행한다. 두 에이전트를 동시에 호출한다.

**호출 트리거**: stage 2 진입 시점과 Step 6의 재리뷰 시점 각각에서, code-reviewer를 호출하기 직전에 Bash 도구로 `git diff --name-only <pullRemote>/<baseBranch>...HEAD`를 재실행해 `CHANGED_FILES`를 갱신한다. Step 4에서 산출한 값을 재사용하지 않는다 — review-fix commit이 신규 파일을 추가하면 고정된 목록은 그 파일을 스코프에서 누락시킨다.

**code-reviewer** — 스코프는 위에서 갱신한 `CHANGED_FILES` 목록으로 한정한다. 호출 프롬프트에 그 경로 목록을 명시 목록으로 실어 보낸다. code-reviewer는 그 목록 안에서 함수 단위 정확성·보안만 본다. stage 1이 lock한 구조 배치(파일 위치·모듈 경계·추상 수준)는 재론하지 않는다.

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

**활성화 조건**:

```
(topicTier == high OR adversarial_enabled == true) AND codex.available AND codex.authenticated
```

```bash
python3 .tack/scripts/dev_context.py read --field=config.review.adversarial_enabled
python3 .tack/scripts/dev_context.py read --field=config.codex.available
python3 .tack/scripts/dev_context.py read --field=config.codex.authenticated
```

아래 순서로 평가하고 첫 매치만 적용한다 (미정의/빈값은 false로 취급). `topicTier`는 Step 4.5에서 산출한 값이다.

1. `topicTier != high` AND `adversarial_enabled`이 false이거나 미정의 → `skipReason="disabled"` (조용히 skip, 경고 없음)
2. `codex.available`이 false이거나 미정의 → `skipReason="codex unavailable"` (경고 출력)
3. `codex.authenticated`이 false이거나 미정의 → `skipReason="codex not authenticated"` (경고 출력)
4. 그 외 → 아래 실행 흐름 진행

`topicTier == high`이면 1번 항목을 통과하므로 adversarial 리뷰가 자동 승격된다. `config.review.adversarial_enabled`는 `low`·`normal` 토픽의 수동 승격 채널로 존속한다.

`low`·`normal` 토픽의 활성화 방법 (기본값 false, 명시적 opt-in 필요):
```bash
python3 .tack/scripts/dev_context.py set-field \
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
- `reviewer`: architect (stage 1) | code-reviewer | security-reviewer | adversarial-review
- `status`: fixed | deferred

severity가 명시되지 않은 adversarial-review 이슈(설계 challenge 등)는 처리 내역 표에서 제외하고 `## Adversarial Review` 원문 섹션에 보존한다.

### 9. Write review-report file

파일 경로:
```
.tack/local/active/<topic>/review-report-<YYMMDDHHmmss>.md
```

`.tack/contracts/review-report.md`의 Required Format을 준수해 파일을 작성한다.

`topicTier != high`인 경우 `architect (stage 1)` 행은 `skipped` / skipReason `topicTier not high`로 적고, `## Architecture Review (stage 1)` 섹션 본문에 `skipped: topicTier not high`를 적는다. lock 판정을 기록하는 주체는 `/flow-review`이며 architect의 `tools`(`Read, Grep, Glob`)는 확장하지 않는다.

```markdown
# Review Report

- topic: <topic>
- timestamp: <YYMMDDHHmmss>
- baseBranch: <baseBranch>

## Reviewers

| reviewer | status | skipReason |
|---|---|---|
| architect (stage 1) | run \| skipped | <skipReason 또는 —> |
| code-reviewer | run \| skipped | — |
| security-reviewer | run \| skipped | — |
| adversarial-review | run \| skipped | <skipReason 또는 —> |

## Architecture Review (stage 1)
<architect 원문 출력 — 8문항 판정 + 근거>

<lock: locked \| blocked — topicTier == high인 보고서에만 적고, 그 외에는 이 라인을 생략>

## Tier Notes
<tier 이상값·필드 부재 노트 한 줄씩, 없으면 "—">

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

### 9.5. Human Gate (`topicTier == high`)

`topicTier == high`인 토픽에서만, review-report 파일 작성(Step 9)을 마친 뒤 완료 보고(Step 10) 직전에 1회 실행한다. `topicTier ∈ {low, normal}`이면 이 단계를 건너뛰고 Step 10으로 진행한다. `/flow-impl`의 배치 루프와 무관한 단계이며, 리뷰 1회당 1회만 발동한다.

`lock: blocked` 경로(Step 5-B)에서는 이 단계가 발동하지 않는다 — 그 경로는 stage-1-only 보고서를 쓴 뒤 Step 5-B에서 정지하며 Step 9·9.5·10에 도달하지 않는다.

**호출 트리거**: 위 조건이 성립하면 `AskUserQuestion`을 다음 형태로 호출한다. 도구가 제공되지 않아 호출이 실패하면 아래 headless fail-safe 분기로 진행한다.

```
AskUserQuestion({
  questions: [{
    question: "high tier 토픽의 리뷰가 완료됐습니다 (CRITICAL <N> / HIGH <N>, adversarial: <run|skipped(<skipReason>)>, 보고서: <path>). 다음 단계로 진행할까요?",
    header: "리뷰 승인",
    multiSelect: false,
    options: [
      { label: "승인 (Recommended)", description: "리뷰 결과를 승인하고 완료 보고를 출력합니다" },
      { label: "보류", description: "review:in-progress 상태를 유지하고 여기서 정지합니다" }
    ]
  }]
})
```

- **승인** → Step 10으로 진행한다.
- **보류** → 토픽 상태를 `review:in-progress`로 유지하고 정지한다. 상태 전환을 실행하지 않는다.

**headless·CI 환경 fail-safe**: `AskUserQuestion` 호출이 실패하면 승인 없이 진행하지 않는다. 다음을 출력하고 정지한다:

```
high tier 토픽은 완료 전 사용자 승인이 필요하지만 대화형 승인을 사용할 수 없는 환경입니다.
보고서: .tack/local/active/<topic>/review-report-<YYMMDDHHmmss>.md

보고서는 이미 작성돼 있으므로 대화형 세션에서 /flow-review를 다시 실행해도
stage 1은 재실행되지 않습니다 (lock: locked 재사용). stage 2와 adversarial은 재실행됩니다.
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
