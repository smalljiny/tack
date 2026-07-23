---
version: 6
name: wf-continuous-learning
description: Use after long sessions or when you notice a recurring pattern. Guides how to extract high-quality reusable patterns from sessions and save them to skills/learned/.
origin: harness
category: session-management
---

## When to Activate

- Running `/meta-harness-learn` at the end of a productive session
- Noticing a pattern you've solved the same way multiple times
- After debugging a non-obvious issue that took real effort
- When a workaround or technique feels worth remembering
- Reviewing `skills/learned/` to curate or remove stale entries

## What Is Worth Saving

A pattern is worth saving if it passes all three filters:

1. **Reusable** — will this situation come up again in a different project?
2. **Non-obvious** — would a competent developer already know this without searching?
3. **Generalizable** — is it independent of this specific codebase?

### Save ✅

| Type | Example |
|------|---------|
| `error_resolution` | "When Zod `.transform()` is chained after `.optional()`, the type inference breaks — use `.optional().transform()` and handle undefined explicitly" |
| `user_correction` | "User prefers early-return style over nested if-else for guard clauses" |
| `workaround` | "Vitest's `vi.useFakeTimers()` doesn't work with `setImmediate` — use `vi.runAllTimesAsync()` instead" |
| `debugging_technique` | "For TypeScript path alias errors in Jest, check `moduleNameMapper` before tsconfig paths" |

### Skip ❌

| Type | Example |
|------|---------|
| Simple typo fix | Fixed a missing semicolon |
| One-time issue | Rotated an API key |
| Project-specific logic | Specific domain rule for this app only |
| Already in rules/ | Covered by `.tack/rules/coding-style.md` |

## Output Format

Save to `.claude/skills/learned/<pattern-name>/SKILL.md`:

```yaml
---
version: 1
name: <kebab-case-name>
description: One sentence — when to recall this pattern
origin: learned
learned_at: <ISO 8601 date>
---

## When to Activate

[Trigger conditions — what situation brings this pattern to mind]

## Pattern

[The concrete technique, workaround, or approach]

## Example

[Minimal code or command that demonstrates it]

## Why It Works

[Optional: brief explanation if non-obvious]
```

## Extraction Process

When running `/meta-harness-learn`:

### 1. Scan session log

Read `.claude/sessions/<today>.jsonl` to find tool-call clusters that suggest repeated effort:
- Multiple Edit calls on the same file
- Bash commands retried with variations
- High tool-call density in a short window

### 2. Identify candidate patterns

Look for:
- **Corrections**: places where an approach was abandoned and retried
- **Repetition**: the same technique applied 2+ times
- **Surprises**: a result that wasn't the first expected outcome

### 3. Apply quality filters

For each candidate, answer:
- Would I look this up again in a future project? → Save
- Is this covered in `rules/` or an existing skill? → Skip
- Is this specific to this project's domain logic? → Skip

### 4. Write the skill file

Keep it short — a good learned skill is under 30 lines. If it needs more, it belongs in `skills/` as a full skill, not `learned/`.

### 5. Curate `skills/learned/`

**Only run this step when explicitly requested by the user.**

Before removing any entry, confirm with the user.

After saving, scan existing entries and remove any that are:
- Superseded by a rule added since
- No longer accurate (library behavior changed)
- Too vague to be actionable

## Confidence and Freshness

Learned skills decay. When revisiting `skills/learned/`:

- If a skill has been useful in the last month → keep
- If a skill hasn't been recalled in 3+ months → consider removing
- If a skill contradicts current `rules/` → remove and update the rule instead

## Connection to /meta-harness-learn

This skill defines the *quality criteria* for `/meta-harness-learn`. The `/meta-harness-learn` skill does the mechanics (read log, write file); this skill defines what's worth writing.
