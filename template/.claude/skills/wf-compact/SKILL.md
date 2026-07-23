---
version: 4
name: wf-compact
description: Use when approaching context limits or between workflow phases. Defines safe compaction points so /compact runs at logical boundaries, not arbitrary mid-task interruptions.
origin: harness
category: session-management
---

## When to Activate

- Session is running long and approaching context limits
- Transitioning between major workflow phases (`/flow-plan` → `/flow-impl`)
- After completing a Task, before starting the next
- When responses feel slower or less coherent (context pressure)
- After a failed approach — clear the dead-end reasoning before retrying
- The `suggest-compact` hook has fired (50+ tool calls)

## Why Strategic Compaction

Auto-compaction triggers at arbitrary points — often mid-task:

```
BAD:  /flow-impl Task 1 → [auto-compact mid-edit] → loses variable names, file paths
GOOD: /flow-impl Task 1 → commit → [/compact] → /flow-impl Task 2
```

Strategic compaction at logical boundaries preserves context through phases.

## Compaction Decision Table

| Phase Transition | Compact? | Reason |
|-----------------|----------|--------|
| `/flow-topic` → `/flow-plan` | Yes | Exploration context is bulky; plan is the output |
| `/flow-plan` → `/flow-impl` | Yes | Plan is saved to file; free up context for code |
| Task N → Task N+1 | Yes | Each Task is a clean boundary |
| `/flow-impl` → `/flow-review` | Maybe | Keep if review needs recent code context |
| `/flow-review` → `/flow-verify` | Yes | Review findings saved; clear before running gates |
| Mid-implementation | **No** | Losing variable names, file paths, partial state is costly |
| After a failed approach | Yes | Clear dead-end reasoning before retrying |

## What Survives Compaction

| Persists ✅ | Lost ❌ |
|------------|--------|
| CLAUDE.md instructions | Intermediate reasoning |
| TodoWrite task list | Previously read file contents |
| Memory files (`~/.claude/memory/`) | Tool call history |
| Git state (commits, branches) | Verbally stated preferences |
| Files on disk (spec.md, plan.md) | Multi-step conversation context |

**Before compacting**: save important context to `.tack/local/<topic>/` or memory.

## Compacting with Intent

Add a focus message to guide the next phase:

```
/compact Focus on implementing Task 2: add JWT validation middleware
/compact Plan is approved. Next: implement T1 - database schema migration
```

## Best Practices

1. **Compact after planning** — Once `implementation-plan.md` is written, compact to start fresh
2. **Compact after debugging** — Clear error-resolution context before continuing
3. **Don't compact mid-implementation** — Preserve context for related changes
4. **Write before compacting** — Save important context to files first
5. **Trust the hook** — `suggest-compact.js` tells you *when*; you decide *if*

## Token Optimization Tips

- Keep CLAUDE.md lean — it's loaded every session
- Skills load on demand; don't pre-load all of them
- Avoid reading large files repeatedly — read once, reference by name
- Duplicate rules between `~/.claude/rules/` and `.claude/rules/` waste tokens

## Hook

`suggest-compact.js` counts tool calls and warns at 50 calls (then every 25):

```
[StrategicCompact] 50 tool calls — consider /compact before starting the next Task
[StrategicCompact] 75 tool calls — good checkpoint for /compact if context feels stale
```

The hook is non-blocking — it only suggests, never interrupts.
