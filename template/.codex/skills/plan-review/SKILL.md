---
version: 4
name: plan-review
description: >-
  Review an implementation plan against an 8-point quality gate. Resolves plan
  path from: (1) explicit argument, (2) dev-context.js read --field=plan, or
  (3) user prompt. Always reads spec separately via dev-context.js read
  --field=spec. Returns READY only when all 8 checks pass; READY WITH NOTE when
  non-blocking observations exist; otherwise NOT READY with concrete fixes
  required. On READY/READY WITH NOTE transitions topic to plan:confirmed; on
  NOT READY reverts to plan:ready.
---

# Plan Review

## Overview

Run a strict pre-implementation verification pass for one implementation plan.
Evaluate all 8 mandatory checks against the corresponding spec and produce a review report.

## Required Inputs

### Plan path resolution (priority order)

Resolve the plan path using the first matching source:

1. **Explicit argument** — user provides the path directly:
   ```
   codex "plan-review 스킬로 .tack/local/active/<topic>/implementation-plan.md를 리뷰해줘"
   ```

2. **Auto-resolution** — read from dev-context.json:
   ```bash
   node .tack/scripts/dev-context.js read --field=current_topic
   # then:
   node .tack/scripts/dev-context.js read --topic=<current_topic> --field=plan
   ```

3. **User prompt** — neither applies; ask the user for the plan path before proceeding.

**Mismatch handling**: If an explicit plan path was provided and it differs from
`topics[current_topic].plan`, ask the user before proceeding:
```
이 계획 파일을 리뷰할까요? 현재 등록된 토픽과 다릅니다. (명시 경로: `<explicit-path>`, 등록 경로: `<topics[current_topic].plan>`)
```
Use the user's selection.

### Spec path resolution (always separate from plan)

Always read the spec path independently:
```bash
node .tack/scripts/dev-context.js read --topic=<current_topic> --field=spec
```

Do not infer the spec path from the plan path or directory.

### Derived values

- Review report path → `<dirname(plan)>/plan-review-<yymmddhhmmss>.md`
  where `<yymmddhhmmss>` is the current local datetime at review time
  (e.g. `plan-review-260415143022.md`)

## Review Workflow

### 1. Load context

- Determine plan path (see Required Inputs above)
- Determine spec path (always via `dev-context.js read --field=spec`)
- Read both documents in full
- Read `.tack/rules/git-workflow.md` for commit convention rules (type allowlist, scope warning level)
- Read `.tack/commit-scopes.md` for project-specific scope list. Parse scope values using regex `^\|\s*([a-z0-9_-]+)\s*\|` on each line, excluding rows where the captured value is `scope` (header) or matches `^-+$` (separator)

### 2. Evaluate the 8 mandatory checks

Apply the checklist in `references/checklist-template.md`.

**Commit 섹션 검증** (warning level, not a separate check — apply within check 4 "완료 기준 명확성"):

For each Story block that contains a `**Commit**:` field (plans written after `pr-driven-commit-workflow` Task 4):
- `type` must be one of: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `ci` → warn if not
- `scope` should match an entry in `.tack/commit-scopes.md` (free-form is acceptable) → warn if not in list
- `subject` must be 72 characters or fewer → warn if exceeded
- Each Story's commit should reflect only that Story's output → flag if the message appears to cover multiple Stories

**If a Story has no `**Commit**` field**: skip Commit validation for that Story (backward-compatible). Do not fail the plan for missing Commit fields.

**Task 라인 first-line subject 검증** (warning level, fold-in within check 4 "완료 기준 명확성"):

For each Story's `**Tasks**:` list, validate every `- [ ] T<storyN>.<taskM> — <subject>` line:
- Subject must be non-empty → warn if missing
- Subject must be 80 characters or fewer → warn if exceeded
- Subject must be a single-line imperative phrase (TaskCreate-compatible) → warn if line wraps or contains markup

This check produces warnings; it does not add a 9th checklist item — Checklist remains 8 fixed lines.

### 3. Produce decision

| Condition | Decision |
|-----------|----------|
| All 8 checks PASS | **READY** |
| All PASS or NOTE, no FAIL | **READY WITH NOTE** |
| Any check FAIL | **NOT READY** |

### 4. Persist review artifacts

- Write the review report to `<dirname(plan)>/plan-review-<yymmddhhmmss>.md`.
- Update dev-context.json state:

| Decision | State Transition | Field Update |
|----------|-----------------|--------------|
| READY / READY WITH NOTE | `node .tack/scripts/dev-context.js update-state --topic=<name> --phase=plan --status=confirmed` | `set-field --field=planReview --value=<path>` |
| NOT READY | `node .tack/scripts/dev-context.js update-state --topic=<name> --phase=plan --status=ready` | `set-field --field=planReview --value=<path>` |

Always write `planReview` regardless of decision.

## Output Format

See `.tack/contracts/plan-review.md` for the canonical report format.

The report written to disk must follow this structure exactly:

```markdown
# Plan Review Result

- Plan: <plan-path>
- Spec: <spec-path>
- Decision: READY | READY WITH NOTE | NOT READY

## Checklist
- [PASS|FAIL|NOTE] 1. 목표 커버리지 - <evidence>
- [PASS|FAIL|NOTE] 2. Non-goals 준수 - <evidence>
- [PASS|FAIL|NOTE] 3. Story 독립성 - <evidence>
- [PASS|FAIL|NOTE] 4. 완료 기준 명확성 - <evidence>
- [PASS|FAIL|NOTE] 5. Story 타입 정확성 - <evidence>
- [PASS|FAIL|NOTE] 6. Story 규모 적정성 - <evidence>
- [PASS|FAIL|NOTE] 7. 구현 순서 타당성 - <evidence>
- [PASS|FAIL|NOTE] 8. 범위 초과 없음 - <evidence>

## Notes
- <only include when Decision is READY WITH NOTE>

## Required Fixes
- <only include when Decision is NOT READY>
```

## Resources

- `references/checklist-template.md`: 8-check template with per-check evaluation instructions.
- `.tack/contracts/plan-review.md`: Canonical format contract for this report.
- `.tack/contracts/implementation-plan.md`: Expected structure of the plan under review.
- `.tack/rules/git-workflow.md` (Read): Commit convention rules (type allowlist, review-fix policy).
- `.tack/rules/` (Read): Shared project rules for context.
- `.tack/commit-scopes.md` (Read): Project-specific scope list for Commit field validation.
- `.tack/local/dev-context.json`: Context source.
