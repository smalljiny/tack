---
version: 3
name: meta-harness-audit
description: Run a deterministic harness health audit and return a prioritized scorecard. User-invocable via /meta-harness-audit.
origin: harness
user-invocable: true
---

# /meta-harness-audit

Scores the harness across 7 categories and lists the top actions to improve it.

## Usage

```
/meta-harness-audit [scope] [--format text|json]
```

- `scope`: `repo` (default) · `hooks` · `skills` · `agents`
- `--format`: `text` (default) · `json` for automation

## Execution

Run the script directly — do not invent scores manually:

```bash
node .claude/scripts/harness-audit.js [scope] [--format text|json]
```

## Categories (0–10 each, 70 pts total)

| # | Category | What it checks |
|---|----------|---------------|
| 1 | Tool Coverage | agents, skills, hook scripts, settings.json |
| 2 | Context Efficiency | CLAUDE.md, performance rules, wf-compact |
| 3 | Quality Gates | flow-verify/flow-review/flow-checkpoint skills, testing rules |
| 4 | Memory Persistence | session-start hook, session-logger, sessions/ dir |
| 5 | Eval Coverage | wf-tdd skill, wf-verification skill, /learn |
| 6 | Security Guardrails | security-reviewer agent, security rules, hook guards |
| 7 | Cost Efficiency | performance rules, async hooks, wf-compact |

## Output

Return:
1. Overall score and percentage
2. Per-category scores
3. Failing checks with file paths
4. Top 3 actions (highest points first)

## After the audit

If the score is below 80%:
- Invoke **harness-optimizer** agent to propose and apply the top fix
- Re-run after each change to measure progress

## Example

```
Harness Audit (repo): 54/70  [77%]

  ✅ Tool Coverage          10/10
  ⚠️  Context Efficiency     5/10
  ✅ Quality Gates          8/10
  ...

Top Actions:
  1. [Cost Efficiency] Add .claude/rules/common/performance.md
  2. [Context Efficiency] Add .claude/skills/wf-compact/SKILL.md
  3. [Cost Efficiency] Mark session-logger hook as async
```
