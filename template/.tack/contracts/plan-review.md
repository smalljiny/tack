# Contract: Plan Review Report

- **Producer**: Codex `plan-review` skill (`.codex/skills/plan-review/SKILL.md`)
- **Consumer**: Claude `/flow-impl` (gate check — requires `plan:confirmed` state)

## File Naming

```
.tack/local/active/<topic>/plan-review-<YYMMDDHHmmss>.md
```

The latest review file is determined by descending filename sort (most recent timestamp first).

## Path Resolution Contract

The plan-review skill must resolve two paths before reviewing:

### Plan path (required)
1. Explicit path provided by user
2. `python3 .tack/scripts/dev_context.py read --topic=<current_topic> --field=plan`
3. Ask user if neither is available

**Mismatch handling**: If the explicit path differs from `topics[current_topic].plan`, ask the user:
> "이 계획 파일을 리뷰할까요? 현재 등록된 토픽과 다릅니다. (명시 경로: `<path>`, 등록 경로: `<registered-path>`)"

### Spec path (required — read separately from plan)
Always read via:
```bash
python3 .tack/scripts/dev_context.py read --topic=<current_topic> --field=spec
```

## Required Format

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

## Checklist Definitions

| # | Item | Evaluation Criteria |
|---|------|---------------------|
| 1 | 목표 커버리지 | 스펙의 모든 목표가 하나 이상의 Story에서 다뤄지는가 |
| 2 | Non-goals 준수 | 구현 계획이 스펙의 범위 밖 항목을 구현하지 않는가 |
| 3 | Story 독립성 | 각 Story가 독립적으로 실행 가능한가 |
| 4 | 완료 기준 명확성 | Completion Criteria가 검증 가능한 조건인가 |
| 5 | Story 타입 정확성 | Story 타입이 Tasks 항목과 일치하는가 |
| 6 | Story 규모 적정성 | 각 Story가 단일 커밋 단위로 적절한가 |
| 7 | 구현 순서 타당성 | Story 실행 순서가 의존성과 일관된가 |
| 8 | 범위 초과 없음 | 스펙 범위를 벗어나는 추가 기능을 포함하지 않는가 |

## Decision Rules

| Condition | Decision |
|-----------|----------|
| All 8 checks PASS | **READY** |
| All PASS or NOTE, no FAIL | **READY WITH NOTE** |
| Any check FAIL | **NOT READY** |

## State Transition Responsibility

After writing the report, the Codex plan-review skill must update dev-context.json:

| Decision | State Transition | Field Update |
|----------|-----------------|--------------|
| READY / READY WITH NOTE | `update-state --topic=<name> --phase=plan --status=confirmed` | `set-field --field=planReview --value=<path>` |
| NOT READY | `update-state --topic=<name> --phase=plan --status=ready` | `set-field --field=planReview --value=<path>` |
