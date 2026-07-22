---
version: 4
---

# Performance Optimization

## Model Selection Strategy

Choose the model by task complexity, not habit. Default to the cheapest model that can handle the task.

| Model | Characteristic | When to Use |
|-------|---------------|-------------|
| **Haiku 4.5** | 3× cheaper than Sonnet | Frequent lightweight tasks, simple code generation, worker agents in parallel execution |
| **Sonnet 4.6** | Best coding model | Main development, multi-agent orchestration, complex coding tasks |
| **Opus 4.7** | Deepest reasoning | Architectural decisions, ambiguous requirements, research and analysis |

### Harness Agent Model Rationale

| Agent | Model | Reason |
|-------|-------|--------|
| planner | opus | Ambiguous requirements need deep reasoning to avoid wrong plans |
| tdd-specialist | opus | Test design decisions have cascading impact; wrong tests waste time |
| code-reviewer | opus | Reviewing requires understanding intent, not just syntax |
| architect | opus | Architectural decisions are hard to reverse |
| security-reviewer | sonnet | Pattern matching against known vulnerabilities; Sonnet is sufficient |
| build-error-resolver | sonnet | Error diagnosis is structured; Sonnet handles it well |
| doc-updater | sonnet | Documentation writing does not require deep reasoning |
| refactor-cleaner | sonnet | Mechanical cleanup; Sonnet is sufficient |
| harness-optimizer | sonnet | File-existence checks and configuration proposals |

## Context Window Management

Avoid these tasks when context is above ~80% (last 20% of window):

- Large-scale refactoring across many files
- Feature implementation spanning multiple files
- Debugging complex multi-component interactions

Prefer these tasks when context is high:
- Single-file edits
- Independent utility creation
- Documentation updates
- Simple bug fixes

When approaching the limit mid-task, run `/compact` at a clean boundary
(e.g., after completing a Task, before starting the next one).
See `.claude/skills/wf-compact/SKILL.md` for safe compaction points.

## Extended Thinking

Extended thinking is enabled by default (up to 31,999 tokens for internal reasoning).

Useful for:
- Complex `/flow-plan` sessions with ambiguous requirements
- Architectural decisions in the `architect` agent
- Security analysis in `security-reviewer`

Controls:
- **Toggle**: `Option+T` (macOS) / `Alt+T` (Windows/Linux)
- **Budget cap**: `export MAX_THINKING_TOKENS=10000`

## Build Troubleshooting

When a build fails, delegate immediately — do not debug manually:

1. Invoke **build-error-resolver** agent
2. Fix incrementally; verify after each change
