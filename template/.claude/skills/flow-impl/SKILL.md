---
version: 4
name: flow-impl
description: Execute Stories from the implementation plan. Supports `--all` for sequential batch execution of all remaining Stories. Invokes the Story-Type-appropriate agent (tdd-specialist, prompt-engineer, refactor-cleaner) and code-reviewer per Story. Stops after one Story by default; `--all` or `config.dev_impl.batch_mode=true` runs all remaining Stories sequentially.
origin: harness
user-invocable: true
---

# /flow-impl

Execute Stories from the implementation plan one at a time, or all at once in batch mode.

## Usage

```
/flow-impl               Auto-select the next incomplete Story
/flow-impl "Story 1"     Run by specific Story name
/flow-impl S2            Run by Story ID
/flow-impl --all         Run all remaining incomplete Stories sequentially (batch mode)
```

## Execution Flow

### 1. Read Context, Parse Flags, and Gate Check

1. Parse invocation flags — determine batch mode once before any Story runs:
   - Check if `--all` is present in `$ARGUMENTS`
   - Read batch mode config:
     ```bash
     python3 .tack/scripts/dev_context.py read --field=config.dev_impl.batch_mode
     ```
   - Set `batch = true` if `--all` is present OR (`batch_mode == "true"` AND no explicit Story ID/name argument is given). An explicit Story argument (e.g. `S2`) always runs a single Story regardless of `batch_mode`. Carry this value through all subsequent steps.

   **`currentBatchRunning` lifecycle:**
   - (a) If `batch == true`, read `current_topic` and persist batch state (anticipates item 2):
     ```bash
     python3 .tack/scripts/dev_context.py read --field=current_topic
     python3 .tack/scripts/dev_context.py set-field --field=config.dev_impl.currentBatchRunning --value=true
     python3 .tack/scripts/dev_context.py set-field --field=config.dev_impl.currentBatchTopic --value=<current_topic>
     ```
   - (b) If `batch == false`, check for a stale batch state:
     - **명시적 Story 인자가 주어진 경우 stale 감지를 건너뛴다** (explicit-Story-wins). 이 호출이 Step 11에 도달하면 `currentBatchRunning`은 그때 초기화된다. 배치를 재개하려면 이후 `/flow-impl --all`을 사용한다.
     - 그 외에는 stale 감지를 수행한다:
     ```bash
     python3 .tack/scripts/dev_context.py read --field=config.dev_impl.currentBatchRunning
     ```
     - `"true"` (정확히 일치) → stale batch state detected. Also read `currentBatchTopic` and current active topic:
       ```bash
       python3 .tack/scripts/dev_context.py read --field=config.dev_impl.currentBatchTopic
       python3 .tack/scripts/dev_context.py read --field=current_topic
       ```
       - If `currentBatchTopic` ≠ `current_topic` → **topic mismatch**: silently reset both fields and continue as single-Story:
         ```bash
         python3 .tack/scripts/dev_context.py set-field --field=config.dev_impl.currentBatchRunning --value=false
         python3 .tack/scripts/dev_context.py set-field --field=config.dev_impl.currentBatchTopic --value=false
         ```
       - If topic matches (or `currentBatchTopic` is empty) → use `AskUserQuestion` (include topic name in message):
         - **재개 (Recommended)**: 이전 배치(`<topic>`)를 이어 실행 — override `batch = true`, then execute (a) above
         - **초기화**: persisted batch 상태를 지우고 이 호출은 단일 Story만 실행 — run both reset commands above; continue as single-Story
     - 그 외 모든 값(empty string, `"false"`, 기타) → not stale; continue as single-Story

2. Get the current topic from dev-context.json:
   ```bash
   python3 .tack/scripts/dev_context.py read --field=current_topic
   ```

3. Read `phase` and `status`:
   ```bash
   python3 .tack/scripts/dev_context.py read --topic=<topic> --field=phase
   python3 .tack/scripts/dev_context.py read --topic=<topic> --field=status
   ```

4. Gate + transition: check `phase:status` against the table below. The table is exhaustive — any state not listed stops with the gate failure message.

   | `phase:status` | 동작 |
   |----------------|------|
   | `plan:confirmed` | `python3 .tack/scripts/dev_context.py update-state --topic=<topic> --phase=impl --status=in-progress` 호출 → 이어서 다음 단계로 진행 |
   | `impl:in-progress` | 그대로 다음 단계로 진행 (no-op) |
   | (그 외) | 아래 메시지를 출력하고 정지 |

   `(그 외)` 행의 게이트 실패 메시지:

   ```
   구현을 시작할 수 없습니다.
   현재 상태: <phase>:<status>
   plan:confirmed 또는 impl:in-progress 상태여야 합니다.
   codex "plan-review 스킬을 실행해줘"
   ```

   **update-state 실패 처리**: `plan:confirmed` 행에서 `update-state` 호출이 비-zero exit이면 즉시 정지하고 다음 메시지를 출력한다. `currentBatchRunning`·`currentBatchTopic`은 정리하지 않는다 — Step 11 미도달로 stale 상태가 유지되어 다음 호출에서 재개 다이얼로그가 자연스럽게 발동한다.

   ```
   phase 전환에 실패했습니다 (update-state 비-zero exit).
   dev-context.json 권한 또는 디스크 상태를 확인하고 다시 시도하세요.
   ```

5. Get the plan path and determine which Story to run:
   ```bash
   python3 .tack/scripts/dev_context.py read --topic=<topic> --field=plan
   python3 .tack/scripts/dev_context.py read --topic=<topic> --field=currentStory
   ```
   - Explicit Story argument (not `--all`) → that Story
   - `currentStory` value → that Story
   - Otherwise → first incomplete `[ ]` Story in `implementation-plan.md`

### 2. Understand Story Details

Extract from the plan document:
- **Type**: tdd, config, infra, refactor, prompt, scaffold
- **Risk Tier**: low, normal, high — 값 해석과 필드 부재·이상값 처리는 아래 위임 스킬이 소유한다
- **Goal**: What to achieve
- **Tasks**: Checklist of `- [ ] T<storyN>.<taskM> — <subject>` lines
- **Completion Criteria**: Validation criteria

`**Risk Tier**` 값을 읽은 뒤, tier가 이 Story의 처리에 어떤 영향을 주는지 결정하기 위해 라우팅 소유자를 로드한다:

Load `.claude/skills/wf-risk-routing/SKILL.md` and follow its process.

### 3. **Pre-work briefing and approval**

**Batch mode (Story 2 onward)**: If `batch == true` AND this is not the first Story in the current invocation, skip the full briefing. Print a single line instead:
```
--- Starting Story <ID>: <Name> ---
```
아래 **tier 노트 조건** 중 하나라도 해당하면 그 노트를 이 라인 바로 다음 줄에 출력한다. 그 다음 Step 4로 진행하며 승인을 기다리지 않는다.

**All other cases (first Story, or non-batch)**: Present the full briefing:

```
---
## Pre-work Briefing: [Story ID] [Story Name]

### Story Overview
- Type: [tdd / config / infra / refactor / prompt / scaffold]
- Risk Tier: [low / normal / high]
- Goal: [What to achieve]

### Work Plan
1. [Step 1 in order]
2. [Step 2 in order]

### Affected Files
- `path/to/file.ts` — [Change description]
- `path/to/new-file.ts` — [NEW] [Purpose]

### Caveats
- [Potential issues]
---
```

**tier 노트 조건** (단일 모드·batch 모드 공통, `wf-risk-routing`이 `/flow-impl`에 부여한 보고 의무):

- Story의 `**Risk Tier**` 필드가 없거나 값이 `low`·`normal`·`high` 중 어느 것도 아니면 `normal`로 간주하고 다음 한 줄을 출력한다: `Risk Tier 미기재 또는 이상값 — normal로 처리합니다.`
- Story의 tier가 `high`이면서 Type이 `tdd` 또는 `refactor`이고 plan에 선행 `scaffold` Story가 없으면 다음 한 줄을 출력한다: `high tier + <Type> Story에 선행 scaffold Story가 없습니다 — 골격 의례 없이 진행합니다.` 실행을 중단하지 않으며 Story를 분해하지도 않는다.

단일 모드·첫 Story에서는 브리핑 블록 다음에, batch 모드 Story 2 이후에는 `--- Starting Story ---` 라인 다음에 출력한다.

After the briefing block is printed (closing `---`), **advisor 조건부 호출**을 먼저 수행한다:

**복잡한 Story 판정 조건** — 아래 중 하나라도 해당하면 `advisor`를 호출한다:
- Story Type이 `infra` 또는 `scaffold` (스크립트·코드 변경, 시스템 영향 큼)
- Tasks 수 ≥ 5

조건에 해당하면 `advisor()`를 호출해 설계 상 위험·엣지 케이스·대안을 사전 검토한다.

`advisor()`는 Claude Code 런타임이 제공하는 built-in 도구이며 별도 스킬·에이전트 로드 없이 호출한다. 도구가 노출되지 않은 환경(headless Codex 등)에서는 호출이 실패하므로 경고 메시지를 출력한 뒤 advisor 단계를 건너뛰고 다음 단계로 진행한다 — `simplify`와 동일한 가용성 fallback 패턴이다.

advisor 응답을 반영한 뒤 다음 단계로 진행한다. 이 호출은 `auto_start`와 무관하게 항상 실행된다.

그 다음, auto_start config를 읽는다:

```bash
python3 .tack/scripts/dev_context.py read --field=config.dev_impl.auto_start
```

Branch on the result:
- If the output equals the string `"true"`: print the following line **verbatim** immediately after the briefing block (not merged into it), then proceed to Step 4 without waiting for approval.
  ```
  auto_start 모드: 승인 없이 바로 구현을 시작합니다. (config.dev_impl.auto_start=true)
  ```
- Otherwise (empty string, `"false"`, or any other value): preserve current behavior — do not start implementation without approval.

### 4. Create Task entries for the Story

Step 3 직후, 현재 Story의 `**Tasks**:` 목록을 파싱해 Task 도구 entries를 일괄 생성한다.

**파싱 규칙:**
- 각 `- [ ] T<storyN>.<taskM> — <subject>` 라인을 추출한다 (sub-bullet, 코드 블록, 표는 제외).
- `T<storyN>.<taskM>`을 Task 도구 entry id로 매핑한다.
- subject(라인 첫 줄)를 Task 도구 entry `subject` 필드로 그대로 사용한다.
- `activeForm` 필드는 wf-task-tracking 스킬의 파생 규칙(한국어 종결형 → `X 중`, English imperative → `-ing` 형)으로 생성한다.

**호출 트리거** (prompt-authoring 규칙 7): Step 3 직후, 현재 Story의 Tasks 목록을 파싱해 모든 Task에 대해 `TaskCreate(taskId=T<storyN>.<taskM>, subject=<subject>, activeForm=<derived>, status='pending')`를 일괄 호출한다.

**실패 처리**: TaskCreate 호출 실패 시 stderr에 경고를 출력하고 진행한다 — plan markdown 체크박스가 단일 진실 원천이므로 에이전트 동작은 영향 없다. 에이전트는 wf-task-tracking 스킬의 "실패 처리" fallback에 따라 entry 누락을 호출자에게 보고한 뒤 markdown을 단일 진실 원천으로 계속 작동한다 (Step 9.5는 누락된 entry를 재생성하지 않는다 — `[x]` 라인의 entry 상태만 `completed`로 정렬한다).

**Story 재시도 시 멱등성**: batch_failed 후 같은 Story가 재호출될 수 있다. 동일 `T<storyN>.<taskM>` ID에 TaskCreate가 중복 호출되어 Task 도구가 거부하더라도 본 단계는 stderr 경고 후 계속하며 무해하다 (markdown 단일 진실 원천 + 에이전트 fallback 경로 발동).

### 5. **Automatically invoke agent by Story Type**

**Type: `tdd`** → Invoke **tdd-specialist** agent:
- Write failing tests (RED)
- Confirm tests fail
- Minimal implementation (GREEN)
- Confirm tests pass
- Refactoring (REFACTOR)
- Check coverage

**Type: `prompt`** → Invoke **prompt-engineer** agent:
- Pass: Goal, Eval Cases (from Completion Criteria), Acceptance threshold, target file path
- Agent runs PROPOSE→EVAL→REFINE cycle via `stack-prompt` skill (max 5 iterations)
- Agent reports outcome (success / stagnation / max iterations)

**Type: `refactor`** → Invoke **refactor-cleaner** agent:
- Ensure test coverage exists before refactoring
- Apply incremental structural improvements

**Type: `config`** → Direct handling:
- Change and validate configuration files

**Type: `infra`** → Direct handling:
- Change infrastructure and document

**Type: `scaffold`** → Direct handling:
- 시그니처, 타입/인터페이스, 호출·이벤트 체인 배선, throwing stub을 작성한다. 함수 본문 로직은 작성하지 않는다.
- 완료 판정은 언어별 정적 검사 + entry 모듈 import 스모크로 수행한다. 판정 기준을 적용하기 전에 Read 도구로 `.tack/contracts/implementation-plan.md`를 열어 `### scaffold 완료 판정 (언어별)` 절의 해당 언어 행을 확인한다 — 그 절이 canonical 출처이며 본 스킬은 표를 복제하지 않는다.
- tdd-specialist를 호출하지 않는다. RED-GREEN-REFACTOR 사이클은 골격에 적용하지 않으며, stub을 채우는 후속 구현 Story가 담당한다.
- **호출 트리거** (prompt-authoring 규칙 7): 골격 작성을 마친 직후, 계약 표에서 확인한 언어별 정적 검사 명령과 entry 모듈 import 스모크 명령을 Bash 도구로 각각 1회 실행한다. 두 결과를 Step 6으로 넘어가기 전에 확인한다. Step 7은 이 결과를 재실행 없이 인용한다.

**Batch failure condition**: If the invoked agent (tdd-specialist, prompt-engineer, or refactor-cleaner) reports an unresolvable failure:
- `batch == true`: set `batch_failed = true` with reason "test failure" and proceed to Step 11 (terminal)
- `batch == false`: surface the failure and stop

**Batch failure condition (`scaffold`)**: `scaffold` Story의 정적 검사가 실패하거나 entry 모듈 import 스모크가 실패하면:
- `batch == true`: set `batch_failed = true` with reason "scaffold static check or import smoke failed" and proceed to Step 11 (terminal)
- `batch == false`: surface the failure and stop

### 6. **Automatically invoke code-reviewer agent** (immediately after implementation)

Immediately review the Story code:
- Quality review
- Immediate feedback + fixes

**`tdd` 타입 전용 — simplify 스킬 후속 호출**: code-reviewer 완료 직후, Story Type이 `tdd`이면 외부 plugin 스킬 `simplify`를 Skill 도구로 호출해 실행한다.

- simplify는 외부 plugin으로 설치된 스킬이며, 사용 가능 스킬 목록에 `simplify`가 노출돼 있을 때만 동작한다. 등록되지 않은 환경에서는 이 단계를 건너뛴다.
- simplify는 코드 재사용·효율성·품질을 재검토하고 개선이 있으면 즉시 수정한다.
- `config`·`infra`·`refactor`·`prompt`·`scaffold` 타입은 simplify를 적용하지 않는다. `prompt` 타입은 REFINE 사이클이 품질 개선을 담당한다. `scaffold` 타입은 골격에 본문 로직이 없어 simplify 대상이 아니다.

**`prompt` 타입 — code-reviewer는 comment-only**: `prompt-engineer`가 Eval Acceptance를 달성한 후 code-reviewer가 실행된다. code-reviewer는 **평가 대상 프롬프트 파일을 수정하지 않는다** — 관찰 사항만 보고한다. 프롬프트 파일 수정이 필요하면 `prompt-engineer`를 재호출해 eval 게이트를 다시 통과해야 한다.

**Batch failure condition**: If code-reviewer reports a blocking issue that cannot be resolved automatically:
- `batch == true`: set `batch_failed = true` with reason "blocking review issue" and proceed to Step 11 (terminal)
- `batch == false`: surface the issue and stop

### 7. Verify Completion Criteria

각 Completion Criterion을 단위 점검하고, 통과한 Criterion의 markdown 체크박스를 `[x]`로 갱신한 뒤 PASS/FAIL 근거를 리스트로 출력한다.

**1단계 — Story Type 분기**:

- **`prompt` 타입**: `prompt-engineer` Acceptance 결과를 재사용한다.
  - Acceptance 통과 → 현재 Story의 모든 Eval Case 체크박스를 markdown `- [ ]` → `- [x]`로 Edit한다 (스코프: 현재 Story의 Completion Criteria 한정).
  - Acceptance 미통과 → 기존 batch_failed 정책 적용 (아래 batch failure condition 참조).
- **`tdd` / `config` / `infra` / `refactor` / `scaffold` 타입**: 본 단계에서 LLM이 각 Criterion을 직접 점검한다 (2단계로 진행).

**2단계 — Criterion 단위 점검** (스코프: 현재 Story의 모든 Completion Criteria 라인):

현재 Story의 `**Completion Criteria**:` 목록에서 모든 `- [ ]` 라인을 순회하며 각 Criterion을 점검한다.

**3단계 — 점검 방법**: Criterion 텍스트가 명시한 방법을 적용한다.
- 파일 존재 확인 (`test -f`, `ls`)
- 파일 내용 검사 (`grep`, `rg`, Read 도구)
- 명령 실행 결과 검사 (Criterion이 명시한 명령에 한함)

**4단계 — Bash 도구 호출 트리거 정책** (read-only 명령에 한정):

- **허용 명령** (파일·환경·네트워크를 변경하지 않는 read-only 명령에 한해 Bash 호출 허용):
  - 파일 검사: `test -f`, `test -d`, `ls`
  - 텍스트 검색: `grep`, `rg`, `head`, `tail`, `cat`, `wc`
  - Git read-only: `git diff`, `git log`, `git show`, `git status`, `git branch`
  - Criterion이 백틱 리터럴로 명시한 read-only 명령 (예: `node --test`, `bash -n`, `tsc --noEmit`, `mypy --cache-dir=/dev/null`, `node --check`). 호출 전 다음 mutating 토큰이 인자에 없는지 확인하고, 하나라도 발견되면 Bash 호출을 거부한다: `-delete`, `-exec`, `-execdir`, `-ok`, `>`, `>>`, `rm`, `mv`, `cp`, `chmod`, `chown`, `|` (외부 명령 파이프).
  - entry 모듈 import 스모크는 아래 두 형태만 허용한다. 인터프리터 인라인 payload는 셸을 거치지 않아 위 mutating 토큰 검사가 닿지 않으므로, 토큰 대신 payload 형태를 제한한다.
    - `python3 -c "import <module>"` — `<module>`은 `[A-Za-z_][A-Za-z0-9_.]*`에 일치하는 단일 모듈 경로.
    - `node -e "import('<entry>').catch(e=>{console.error(e);process.exit(1)})"` — `<entry>`는 파일 경로 리터럴. `.catch` 없이 호출하면 import 실패가 unhandled rejection이 되어 종료 코드가 Node 버전에 따라 달라진다.
    - payload에 `;`, 개행, `__import__`, `open(`, `exec`, `eval`, `require(` 중 하나라도 있으면 Bash 호출을 거부한다.
- **빌드·테스트 결과 재사용**: Step 5에서 실행된 빌드·테스트 명령(예: `npm test`, `npm run build`, `jest`, `pytest`, 그리고 `scaffold` Story의 정적 검사·entry 모듈 import 스모크)의 결과는 재실행하지 않고 Step 5 보고 메시지의 마지막 결과 라인(GREEN 확인 라인 / 종료 코드 / stdout 마지막 줄)을 인용해 판정한다.
- **금지**: 파일·환경 변경, 패키지 설치, 네트워크 호출, 위 mutating 토큰을 포함하는 명령. 이들 명령이 필요한 Criterion은 Bash로 실행하지 않고 Read 도구 + Step 5 증거로 판정한다.
- **판정 증거 부재**: Read 도구·Step 5 증거·허용 명령으로도 판정할 수 없으면 FAIL 처리하고 사유에 `evidence-not-available`을 명시한다.

**5단계 — 결과 처리**:
- 통과한 Criterion → markdown `- [ ]` → `- [x]` Edit (현재 Story의 Completion Criteria 한정 스코프).
- 실패한 Criterion → `- [ ]` 유지.

**6단계 — PASS/FAIL 출력 형식** (마크다운 표 아닌 단순 리스트로 출력 — batch 모드 출력량 우려 해소):

각 Criterion 한 줄로 `[PASS] <Criterion 텍스트 요약> — <근거 한 줄>` 또는 `[FAIL] <Criterion 텍스트 요약> — <실패 근거>` 형태로 출력한다.

예시:
```
## Completion Criteria 점검 결과
[PASS] frontmatter version: 21 — grep 결과 일치
[PASS] Step 9.5에 AskUserQuestion 키워드 존재 — 라인 312 매칭
[FAIL] Key Principles에 신규 항목 추가 — 매칭 라인 없음
```

**Batch failure condition**: 1개 이상 Criterion이 FAIL이면:
- `batch == true`: set `batch_failed = true` with reason "completion criteria not met" and proceed to Step 11 (terminal)
- `batch == false`: surface the failure and stop

### 8. Execute Commit

Read the `auto_commit` config:

```bash
python3 .tack/scripts/dev_context.py read --field=config.dev_impl.auto_commit
```

**Find the Commit message** from the current Story's plan block:
- Look for `- **Commit**:` line in the Story section of the plan document
- Extract the subject line (first backtick-quoted value after `**Commit**:`)
- Optionally include the body lines (indented under the subject)

**If no `**Commit**` field exists** in this Story (pre-contract plan or omitted):
```
이 Story에 **Commit** 필드가 없습니다. commit을 건너뛰시겠습니까? (y/skip)
```
- `y` or `skip`: skip commit for this Story and continue to Step 9
- Any other response:
  - `batch == true`: set `batch_failed = true` with reason "user declined to skip commit (no **Commit** field)" and proceed to Step 11 (terminal)
  - `batch == false`: stop

**Stage files**: stage only files changed by this Story. Do **NOT** use `git add -A` or `git add .`.
- Use the list of files from Step 5/6 (tdd-specialist and code-reviewer output) as the staging target.
- **Quote every file path** when passing to `git add` — paths may contain spaces or glob characters: `git add "path/to/file" "other file.ts"`
- Run `git status --short` first, confirm the staged file list with the user if `auto_commit=false`.
- Exclude sensitive files unconditionally: `.env*`, `*.pem`, `*.key`, `credentials.json`.
- When `auto_commit=true`, verify the staged file list against the sensitive file patterns before committing — abort if any match is found regardless of `batch` value.

**If `auto_commit = "true"`**: execute commit automatically using a HEREDOC to avoid shell metacharacter injection:
```bash
git add "<story-file-1>" "<story-file-2>"
git commit -m "$(cat <<'COMMIT_MSG'
<subject>
<body>
COMMIT_MSG
)"
```
Print: `auto_commit: <commit-message>`

**If `auto_commit` is false/empty (default)**: show the planned message and prompt:
```
이 Story의 commit 메시지:
  <commit-subject>
  [<body>]

스테이징 대상 파일: <file list>

지금 commit하시겠습니까? (y/n/skip)
```
- `y`: stage and commit using HEREDOC pattern (never interpolate commit message directly into shell argument)
- `n`:
  - `batch == true`: set `batch_failed = true` with reason "commit refused by user" and proceed to Step 11 (terminal)
  - `batch == false`: stop
- `skip`: skip commit and continue to Step 9 (commit omitted for this Story; not a failure)

**amend is forbidden** — always create a new commit. Review-fix commits from `/flow-review` must also be separate commits (see `.tack/rules/git-workflow.md`).

**Batch failure conditions summary** — any of the following stops the batch loop:
1. tdd-specialist: RED→GREEN test failure unresolved (Step 5)
2. scaffold Story: static check or entry-module import smoke failed (Step 5)
3. code-reviewer: blocking issue unresolved after auto-fix attempt (Step 6)
4. Completion Criteria: one or more criteria fail verification (Step 7)
5. Commit: user responds `n` (commit refused) (Step 8)
6. No `**Commit**` field: user declines to skip (Step 8)
7. Unchecked tasks gate: user selects '실제 미수행' (Step 9.5 게이트)

### 9. Update Plan Document (Story checkbox)

Mark the completed Story:
- Story checkbox: `### [ ] Story N` → `### [x] Story N`

### 9.5. Sync markdown checkboxes from Task tool entries

Step 9 완료 직후, Task 도구 entries 상태를 단일 진실 원천으로 두고 plan markdown의 Task 체크박스를 갱신한다 (entries → markdown 방향).

**호출 트리거** (prompt-authoring 규칙 7): Step 9 완료 직후, 본 단계를 실행한다. 각 entry 상태를 조회하고 아래 분기 표에 따라 markdown을 Edit한다.

**4단계 흐름:**

1. **Tasks 목록 파싱**: 현재 Story의 `**Tasks**:` 목록에서 모든 `- [ ] T<storyN>.<taskM> — <subject>` 라인을 추출한다 (sub-bullet, 코드 블록, 표 라인은 제외).
2. **entry 상태 조회**: 추출된 모든 `T<storyN>.<taskM>` ID에 대해 Task 도구 entry 상태를 조회한다.
3. **분기 처리** (각 Task별):
   - `status=completed` → markdown `- [ ]` → `- [x]` Edit
   - `status=pending` 또는 `status=in_progress` → 미체크 유지 (markdown 변경 없음)
   - entry 없음 (TaskCreate 실패로 누락) → markdown 상태 그대로 유지 (Edit 안 함)
4. **미체크 Task 수집**: 분기 처리 후 markdown에 남아 있는 `- [ ]` Task 라인을 수집한다.
   - 0건 → Step 10으로 진행
   - 1건 이상 → 아래 미체크 Task 게이트 실행

**미체크 Task 게이트**

**호출 트리거** (prompt-authoring 규칙 7): Step 9.5 분기 처리 후 미체크 `[ ]` Task가 1건 이상 남아 있으면 `AskUserQuestion`을 호출한다. 미체크 Task가 0건이면 본 게이트를 건너뛰고 Step 10으로 진행한다. 본 게이트는 단일 모드·batch 모드 모두 일시 중단한다 (Key Principles "fully unattended" 예외 — 데이터 정합성 결정이 자동화 불가).

호출 형태:
```
AskUserQuestion({
  questions: [{
    question: "미체크 Task <N>건이 남아 있습니다. 의도를 알려주세요.",
    header: "Task 게이트",
    multiSelect: false,
    options: [
      { label: "보고 누락 (Recommended)", description: "수행은 됐지만 TaskUpdate(completed) 호출이 누락된 경우" },
      { label: "실제 미수행", description: "Task가 정말 수행되지 않은 경우 또는 Story 정의 결함" }
    ]
  }]
})
```

**옵션 1 (보고 누락) 처리 분기** (순서대로 실행):
- **스코프**: 현재 Story 헤더(`### [ ] Story N` 또는 `### [x] Story N`) 다음 라인부터 다음 Story 헤더 직전까지의 라인만 대상으로 한다. 다른 Story의 체크박스는 변경하지 않는다.
- **1단계 (markdown Edit)**: 위 스코프 내 모든 미체크 Task 라인을 markdown `- [ ]` → `- [x]`로 Edit한다.
- **2단계 (TaskUpdate)**: 미체크였던 모든 `T<storyN>.<taskM>`에 대해 `TaskUpdate(taskId=T<storyN>.<taskM>, status='completed')`를 호출한다.
- **entry 없는 Task** (TaskCreate 실패로 누락된 케이스): markdown `[x]`만 처리하고 entry 생성은 생략한다 — wf-task-tracking fallback 규약을 따른다.
- 처리 후 Step 10으로 진행.

**옵션 2 (실제 미수행) 처리 분기**:
- markdown 체크박스와 Task 도구 entries 모두 변경하지 않는다.
- `batch == false` (단일 모드): 작업 중단. 안내 메시지를 출력한다:
  ```
  미체크 Task가 남아 있습니다. Story를 재실행하거나 plan을 수정한 뒤 다시 시도하세요.
    /flow-impl <story-id>
  ```
- `batch == true` (batch 모드): `batch_failed = true` 설정 (reason: `"user-declared unchecked tasks (real non-execution)"`) → Step 11 terminal로 진행.

### 10. Update dev-context.json

```bash
python3 .tack/scripts/dev_context.py set-field \
  --topic=<topic> --field=currentStory --value=<next-story-id>
```

Use `null` when all Stories are complete:
```bash
python3 .tack/scripts/dev_context.py set-field \
  --topic=<topic> --field=currentStory --value=null
```

### 10.5. Batch Loop Decision

Evaluate after Step 10 (sub-step 0 owns the full skip/recover/proceed logic):

0. Recover persisted batch state (session memory loss guard):
   - If the invocation included an **explicit Story argument** (e.g. `/flow-impl S2`), skip this step entirely (explicit-Story-wins overrides persisted batch state — do not loop).
   - Otherwise, read the persisted fields:
     ```bash
     python3 .tack/scripts/dev_context.py read --field=config.dev_impl.currentBatchRunning
     python3 .tack/scripts/dev_context.py read --field=config.dev_impl.currentBatchTopic
     ```
   - If `currentBatchRunning == "true"` AND `currentBatchTopic` matches the active topic (or `currentBatchTopic` is empty), recover `batch = true` (세션 메모리 소실 보완).
   - If `currentBatchRunning == "true"` AND `currentBatchTopic` ≠ active topic, do not recover — topic mismatch; `batch` remains unchanged.
   - Then proceed only if `batch == true`.

1. Read `currentStory` written by Step 10 — this must equal the first remaining `[ ]` Story in `implementation-plan.md`. If they disagree (plan edited mid-batch), use the plan file as the authoritative source and log a warning.
2. If a next Story exists → jump back to Step 2 (start next Story)
3. If no more incomplete Stories remain → proceed to Step 11 (terminal: batch complete)

### 11. **Output Story completion briefing and stop**

**Per-Story briefing (non-terminal: batch mid-run)**

Reached only when the Batch Loop Decision (Step 10.5) jumps back to Step 2. Not printed separately — the loop continues directly.

**Terminal briefing (single-Story mode, batch complete, or batch stopped)**

단일/배치 모드 무관하게 터미널 브리핑 직전 batch 상태 필드를 초기화한다. reset 명령 실패 시에는 오류를 표시하고 터미널 브리핑을 중단한다:

```bash
python3 .tack/scripts/dev_context.py set-field \
  --field=config.dev_impl.currentBatchRunning --value=false
python3 .tack/scripts/dev_context.py set-field \
  --field=config.dev_impl.currentBatchTopic --value=false
```

*Single-Story mode (non-batch)*:
```
---
## Story Complete: [Story ID] [Story Name]

### Work Summary
- [Implementation/change details]
- [List of created/modified files]

### Test Results
- Tests: PASS ([X] passed)
- Coverage: [X]%

### Next Story
- [Next incomplete Story ID and name]
- Continue with /flow-impl.
---
```

*Batch complete (all Stories finished)*:
```
---
## Batch Complete

Completed [N] Stories:
  [x] Story 1: <name>
  [x] Story 2: <name>
  ...

Next: /flow-review
---
```

*Batch stopped (failure)*:
```
---
## Batch Stopped at Story [ID]: [Name]

Reason: <batch_failed reason>

Completed before stopping:
  [x] Story <n>: <name>  (if any)

Resume after fixing the issue:
  /flow-impl          Resume from the failed Story
  /flow-impl --all    Re-run batch from the failed Story
---
```

**Stop immediately after outputting the terminal briefing. Do not automatically start the next Story.**

## Key Principles

- **One Story at a time (default)** — only one Story per invocation unless `--all` or `config.dev_impl.batch_mode=true` is set; in batch mode all remaining Stories run sequentially
- **Story-start TaskCreate batch** — at Step 4, parse the current Story's `**Tasks**:` list and emit one batched `TaskCreate(pending)` covering every Task before invoking the implementation agent
- **Reverse Step 9.5** — Task 도구 entries 상태가 markdown 체크박스의 단일 진실 원천이며, `/flow-impl`이 Story 종료 시점에 entries → markdown 방향으로 sync한다 (`status=completed` → `[x]`, `pending`·`in_progress` → 미체크 유지, entry 없음 → markdown 그대로)
- **Unchecked-Task gate** — Step 9.5 후 `[ ]` Task가 남으면 단일·batch 모드 모두 사용자에게 의도(보고 누락 / 실제 미수행)를 묻고 분기한다. '보고 누락' → markdown `[x]` + `TaskUpdate(completed)` 처리 후 Step 10 진행, '실제 미수행' → 단일 모드 stop / batch 모드 batch_failed (Step 11)
- **Per-Criterion verification** — Step 7은 각 Completion Criterion을 LLM이 직접 점검 (`prompt` 타입은 prompt-engineer Acceptance 결과 재사용); 통과 Criterion만 `[x]` 갱신 + PASS/FAIL 근거 출력
- **Bash re-run policy in Step 7** — Step 5에서 실행된 빌드·테스트 명령은 재실행하지 않는다; 파일 존재·grep·Criterion 명시 명령에 한해 Bash 호출 허용
- **Batch stops on failure** — any of the 7 failure conditions (test, scaffold static check/import smoke, review, criteria, commit refused, no-commit-field refused, unchecked-task gate) halts the batch immediately; `currentBatchRunning` is reset on every terminal exit (Step 11)
- **Batch persistence** — `currentBatchRunning`·`currentBatchTopic` 필드로 비정상 종료된 배치를 topic-scoped로 감지·재개한다; 토픽 불일치 시 silently reset, Step 11 모든 terminal exit 시 초기화. Step 1 게이트 실패 등 Step 11 미도달 시에는 stale 상태가 유지되어 다음 호출에서 재개 다이얼로그를 트리거한다.
- **Pre-work briefing for first Story only in batch mode** — Story 2 onward shows a single "Starting Story" line; full briefing and approval gate apply only to the first Story (subject to `auto_start`)
- **Prior approval required** (unless `config.dev_impl.auto_start=true`) — do not start the first Story without approving the work plan
- **Gate + transition** — Step 1에서 `phase:status` 상태 테이블로 게이트 검사와 `plan:confirmed → impl:in-progress` 전환을 한 단계에 처리; `update-state` 비-zero exit 시 즉시 정지하고 `currentBatchRunning`·`currentBatchTopic`은 정리하지 않는다
- **Approval rejection no rollback** — 사용자가 briefing 승인을 거절(`n`)해도 phase는 `impl:in-progress`로 유지된다. 게이트가 두 상태 모두 통과시키므로 다음 호출이 자연스럽게 재개된다.
- **TDD enforced** — `tdd` type must write tests first
- **Immediate review** — automatically invoke code-reviewer immediately after implementation
- **simplify after code-review (tdd only)** — `tdd` 타입은 code-reviewer 직후 `simplify` 스킬을 추가 실행; `config`·`infra`·`refactor`·`prompt`·`scaffold` 타입은 제외 (`prompt`는 REFINE 사이클이 담당, `scaffold`는 본문 로직이 없음)
- **scaffold Story handling** — `scaffold` 타입은 Direct handling으로 시그니처·타입·체인 배선·throwing stub만 작성한다. TDD 강제와 simplify에서 제외하며, 완료는 언어별 정적 검사 + entry 모듈 import 스모크로 판정한다 (기준의 canonical 출처는 `.tack/contracts/implementation-plan.md`의 `### scaffold 완료 판정 (언어별)` 절)
- **Pre-work advisor (complex Stories)** — `infra`·`scaffold` 타입 또는 Tasks 수 ≥ 5인 Story는 브리핑 직후 `advisor()`를 호출해 설계 위험·엣지 케이스를 사전 점검
- **Tier note surface** — `**Risk Tier**` 부재·이상값, 그리고 `high` + `tdd`/`refactor`에 선행 `scaffold` Story가 없는 경우를 브리핑(단일 모드) 또는 `--- Starting Story ---` 라인(batch 모드)에 한 줄로 남긴다; 어느 조건도 실행을 중단하지 않는다
- **Commit from plan** — commit message comes from the Story's `**Commit**` field; never invent a message
- **auto_commit default is false** — user sees and approves each commit unless `config.dev_impl.auto_commit=true`
- **batch + auto_start + auto_commit = fully unattended** — enabling all three removes every human gate after Story 1 approval; use only in trusted environments. **예외**: Step 9.5 미체크 Task 게이트는 batch 모드에서도 사용자 응답을 기다린다 — 데이터 정합성(`보고 누락` vs `실제 미수행` 구분)이 자동 결정 불가능한 의도된 동작이다.
- **Explicit Story overrides batch_mode** — `/flow-impl S2` always runs a single Story regardless of `config.dev_impl.batch_mode`; `--all` always activates batch mode
- **amend forbidden** — always create a new commit; review-fix commits are separate

## Next Steps

After all Stories complete (single-Story or batch): final full review with `/flow-review`
