---
version: 4
---
# Agent Coordination Rules

## Available Agents

Located in `.claude/agents/`:

| Agent | Role | When to Activate |
|-------|------|-----------------|
| planner | Implementation planning | Complex feature requests, refactoring |
| tdd-specialist | Test-driven development | New features, bug fixes |
| code-reviewer | Code quality review | Immediately after writing code |
| security-reviewer | Security vulnerability analysis | Before commits, sensitive code changes |
| architect | System design | Architecture decisions, design reviews, `/flow-review` stage 1 (structural verdict on `high` tier topics) |
| build-error-resolver | Build error resolution | Build/type errors |
| doc-updater | Documentation sync | After implementation is complete |
| refactor-cleaner | Dead code cleanup | Code maintenance |

## Immediate Agent Activation

Auto-activate in the following situations without user request:

1. Complex feature requests → **planner**
2. Immediately after writing/modifying code → **code-reviewer**
3. New features or bug fixes → **tdd-specialist**
4. Architecture decisions → **architect**
5. `/flow-review` stage 1 on a `topicTier == high` topic → **architect** (structural verdict before unit review)
6. Build/type errors → **build-error-resolver**

## Parallel Execution

Always run independent tasks in parallel:

```
# GOOD: Parallel execution
Agent 1: Security analysis of auth.ts
Agent 2: Performance review of cache system
Agent 3: Type checking of utils.ts

# BAD: Unnecessary sequential execution
Wait for agent 1, then agent 2, then agent 3
```

## Multi-Perspective Analysis

Use role-separated sub-agents for complex problems:
- Factual Reviewer
- Senior Engineer
- Security Expert
- Consistency Reviewer

## Tool Usage Discipline

### Read-before-Edit

The Edit tool requires the target file to have been Read in the same conversation turn.
**Always call Read before Edit** — even for files you've seen in previous turns.

### Parallel Edit Pattern

When editing multiple files in the same step:

```
# GOOD: Read all files first, then Edit in a separate block
Step 1 — Read block:  Read(file-a), Read(file-b), Read(file-c)  [parallel]
Step 2 — Edit block:  Edit(file-a), Edit(file-b), Edit(file-c)  [parallel]

# BAD: Read and Edit mixed in one block
Read(file-a) + Edit(file-a) in the same tool-call block
→ Edit may execute before its Read result is available
```

### Bash Edits

When delegating file edits to Bash (e.g., `sed`, `awk`), the Read-before-Edit rule does not
apply technically, but read the file first anyway to verify the content before modifying it.

### Stated Invocation Form

커맨드·스킬·문서의 명세에 적힌 CLI 호출 형태(`<cmd> <subcmd> --flag=val`)는 명세대로 사용한다. 인자를 생략해 dump나 도움말 동작을 추측하지 않는다.

근거:
- 하네스 CLI는 의도적으로 인자 단위 조회만 허용한다. 예: `dev-context.js read`는 `--field`가 필수이고, 인자 없는 호출은 사용법을 stderr로 출력하며 비제로 종료한다.
- 명세에 적힌 호출은 설계 의도를 반영한 계약이다. 자체 단축은 계약을 깨고, 후속 호출자(다음 LLM 또는 사용자)에게 잘못된 휴리스틱을 학습시킨다.

호출 형태가 불확실하면 명세 본문을 다시 읽는다. `--help`를 문서로 명시한 CLI에 한해 인자 없는 호출을 사용한다.
