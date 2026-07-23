---
version: 6
name: spec-review
description: >-
  Review a spec document against an 8-point quality gate. Resolves spec path from:
  (1) explicit argument, (2) dev-context.js read --topic=<name> --field=spec, or
  (3) user prompt. Returns READY only when all 8 checks pass; READY WITH NOTE when
  non-blocking observations exist; otherwise NOT READY with concrete fixes required.
---

# Spec Review

## Overview

Run a strict pre-planning verification pass for one spec document.
Evaluate all 8 mandatory checks and produce a review report.

## Required Inputs

### Spec path resolution (priority order)

Resolve the spec path using the first matching source:

1. **Explicit argument** — user provides the path directly:
   ```
   codex "spec-review 스킬로 .tack/local/backlog/<topic>/spec.md를 리뷰해줘"
   ```

2. **Auto-resolution** — read from dev-context.json via CLI:
   ```bash
   node .tack/scripts/dev-context.js read --field=current_topic
   # then:
   node .tack/scripts/dev-context.js read --topic=<current_topic> --field=spec
   ```

3. **User prompt** — neither applies; ask the user for the spec path before proceeding.

If the user explicitly provides a spec path, always use it regardless of `dev-context.json` content.

### Derived values

- Review report path → `<dirname(spec)>/spec-review-<yymmddhhmmss>.md`
  where `<yymmddhhmmss>` is the current local datetime at review time (e.g. `spec-review-260415143022.md`)

## Review Workflow

### 1. Load context

- Determine spec path (see Required Inputs above)
- Read the spec document in full
- Read project rules from `.tack/rules/` (shared) and `.claude/rules/` (Claude operational) where relevant

### 2. Evaluate the 8 mandatory checks

Apply the checklist in `references/checklist-template.md`.
See `references/rules-and-inputs.md` for context loading rules and field definitions.

### 3. Produce decision

| Condition | Decision |
|-----------|----------|
| All 8 checks PASS | **READY** |
| All PASS or NOTE, no FAIL | **READY WITH NOTE** |
| Any check FAIL | **NOT READY** |

### 4. Persist review artifacts

- Write the final review report to `<dirname(spec)>/spec-review-<yymmddhhmmss>.md`.
- Determine the owning topic before writing `specReview`:
  1. Read `current_topic`:
     ```bash
     node .tack/scripts/dev-context.js read --field=current_topic
     ```
  2. Read that topic's registered spec path:
     ```bash
     node .tack/scripts/dev-context.js read --topic=<current_topic> --field=spec
     ```
  3. **If the resolved spec path does not match the spec actually reviewed**, ask the user:
     ```
     리뷰한 스펙 경로(<reviewed-path>)가 현재 토픽(<current_topic>)에 등록된 경로(<registered-path>)와 다릅니다.
     specReview 필드를 업데이트할 토픽을 확인해주세요:
       1. <current_topic> (등록 경로 무시)
       2. 업데이트 안 함
     ```
     Do not silently write to the wrong topic.
- Update `.tack/local/dev-context.json` via CLI (Codex owns this update):
  ```bash
  node .tack/scripts/dev-context.js set-field \
    --topic=<confirmed_topic> \
    --field=specReview \
    --value=<report-path>
  ```
- If the report cannot be written, state that clearly.

## Output Format

See `.tack/contracts/spec-review.md` for the canonical format contract.

The review report written to disk must use this exact structure:

```markdown
# Spec Review Result

- Spec: <spec-path>
- Decision: READY | READY WITH NOTE | NOT READY

## Checklist
- [PASS|FAIL|NOTE] 1. 목표 명확성 - <evidence>
- [PASS|FAIL|NOTE] 2. Non-goals 명시 - <evidence>
- [PASS|FAIL|NOTE] 3. 아키텍처 충분성 - <evidence>
- [PASS|FAIL|NOTE] 4. 의사결정 근거 - <evidence>
- [PASS|FAIL|NOTE] 5. Open Questions - <evidence>
- [PASS|FAIL|NOTE] 6. 내부 일관성 - <evidence>
- [PASS|FAIL|NOTE] 7. 구현 가능성 - <evidence>
- [PASS|FAIL|NOTE] 8. 범위 적정성 - <evidence>

## Notes
- <only include when Decision is READY WITH NOTE>

## Required Fixes
- <only include when Decision is NOT READY>
```

Use `[NOTE]` for non-blocking observations.

## Resources

- `references/checklist-template.md`: 8-check template with per-check evaluation instructions.
- `references/rules-and-inputs.md`: Context loading rules, field definitions, fallback inputs.
- `.tack/contracts/spec-review.md`: Canonical format contract for this report.
- `.tack/rules/` (Read): Shared coding-style, git-workflow, testing, security, typescript rules — referenced during load context.
- `.tack/local/dev-context.json`: Context source.
