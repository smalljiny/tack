---
version: 1
name: skill-checklist-duplication
description: 커맨드가 스킬의 체크리스트를 bullet으로 직접 나열하면 component-boundaries 위반 — 스킬 섹션 참조 문구로 교체해야 한다
origin: learned
learned_at: 2026-04-22
---

## When to Activate

커맨드 파일 작성 시 스킬이 이미 정의한 체크리스트·패턴·규칙을 bullet으로 나열하려는 순간.

## Pattern

스킬에 이미 존재하는 체크리스트를 커맨드에 복사하지 않는다. 대신 스킬 섹션을 참조하는 한 줄로 위임한다:

```markdown
Walk through the **<Checklist Name>** from `<skill-path>` (section "<Section Name>").
```

## Example

```markdown
# BAD — 스킬 내용 복사 (component-boundaries 위반)
### 3. Run Safety Checklist
- [ ] Migration has both UP and DOWN
- [ ] No full table locks on large tables
- [ ] New columns have defaults or are nullable
...

# GOOD — 스킬에 위임
### 3. Run Safety Checklist
Walk through the **Migration Safety Checklist** from
`.claude/skills/stack-db-migrations/SKILL.md` (section "Migration Safety Checklist").
```

## Why It Works

스킬이 Single Source of Truth가 된다. 커맨드가 복사본을 갖고 있으면 스킬 업데이트 시 드리프트가 발생한다. component-boundaries.md의 "already exists in a skill (duplication)" 기준에 해당한다.
