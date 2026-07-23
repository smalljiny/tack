---
version: 1
name: meta-harness-learn
description: Analyze patterns used repeatedly in the current session and save them as reusable skills. User-invocable via /meta-harness-learn.
origin: harness
user-invocable: true
---

# /meta-harness-learn

Extract reusable patterns from the current session and save them to `.claude/skills/learned/`.

## Execution Flow

1. Verify `.claude/sessions/` exists and contains log files for the current session.
2. Load `.claude/skills/wf-continuous-learning/SKILL.md` and follow **Steps 1–4 only** (scan, identify, filter, write). Do **not** execute Step 5 (Curate — deleting existing entries).
3. On completion, show a summary:

   ```
   학습 완료

   새로 저장된 스킬:
   - [pattern-name]: [description]

   저장 위치: .claude/skills/learned/
   ```

   If no patterns met the quality bar, say so explicitly.

## Curation (Opt-in)

Step 5 of the skill (removing stale or superseded entries) is **not run by default**.
To curate existing learned skills, ask explicitly:

```
.claude/skills/learned/ 의 기존 스킬을 정리해줘
```

Before removing any entry, confirm with the user.

## Notes

- Default run is **non-destructive**: only adds new skill files, never deletes existing ones.
- Curation requires explicit intent because deletion of learned skills is hard to reverse without git.
