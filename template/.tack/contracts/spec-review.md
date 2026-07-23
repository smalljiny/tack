# Contract: Spec Review Report

- **Producer**: Codex `spec-review` skill (`.codex/skills/spec-review/SKILL.md`)
- **Consumers**: Claude `/flow-spec` (reads Decision to confirm spec), Claude `/flow-plan` (gate check)

## File Naming

```
.tack/local/backlog/<topic>/spec-review-<YYMMDDHHmmss>.md
.tack/local/active/<topic>/spec-review-<YYMMDDHHmmss>.md
```

The latest review file is determined by descending filename sort (most recent timestamp first).

## Required Format

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

## Decision Rules

| Condition | Decision |
|-----------|----------|
| All 8 checks PASS | **READY** |
| All PASS or NOTE, no FAIL | **READY WITH NOTE** |
| Any check FAIL | **NOT READY** |

Use `[NOTE]` for non-blocking observations.

## State Transition Responsibility

After writing the report, the Codex spec-review skill must update dev-context.json:

- `READY` / `READY WITH NOTE` → no state transition (Claude `/flow-spec` handles `spec:confirmed`)
- `NOT READY` → no state transition (Claude `/flow-spec` handles `spec:drafting` rollback)
- Always: `dev-context.js set-field --topic=<name> --field=specReview --value=<report-path>`
