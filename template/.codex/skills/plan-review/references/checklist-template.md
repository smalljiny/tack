# Plan Review Checklist Template

Use all 8 items. Evaluate the implementation plan against the corresponding spec.

Final decision rules:
- All PASS → **READY**
- Any FAIL → **NOT READY**
- All PASS but some NOTE observations → **READY WITH NOTE**

---

- [ ] 1. 목표 커버리지 (Goal Coverage)
  Evidence: (verify every goal stated in the spec's Goals section is addressed by at least one Story.
  Check: for each spec goal, identify the Story(s) that implement it.
  Any spec goal with no corresponding Story → FAIL.
  Partial coverage with clear gaps → FAIL.)

- [ ] 2. Non-goals 준수 (Non-goals Respected)
  Evidence: (verify the implementation plan does not include Stories that implement items
  listed in the spec's Non-goals section.
  Any Story implementing a spec Non-goal → FAIL.
  Stories that appear to approach a Non-goal boundary → NOTE.)

- [ ] 3. Story 독립성 (Story Independence)
  Evidence: (verify each Story can be executed and committed independently.
  Check: does completing Story N require partially-complete state from Story M where M > N?
  Hidden shared state, build-breaking intermediate steps → FAIL.
  Documented sequential dependencies with clear rationale → acceptable.)

- [ ] 4. 완료 기준 명확성 (Completion Criteria Verifiable)
  Evidence: (verify every Story's Completion Criteria are objectively verifiable.
  Accepted forms: runnable command, observable file output, test pass/fail, explicit assertion.
  Vague criteria like "works correctly" or "looks good" → FAIL.
  Missing Completion Criteria section in any Story → FAIL.

  Task line first-line subject validation (warning level, fold-in here):
  - Each Task line `- [ ] T<storyN>.<taskM> — <subject>` must have a non-empty subject → warn if missing.
  - Subject must be 80 characters or fewer → warn if exceeded.
  - Subject must be a single-line imperative phrase (TaskCreate-compatible) → warn if it wraps or contains markup.

  Tasks 보존·검증 의무 ↔ Completion Criteria 1:1 매핑 — Tasks에 `preserve X` / `do not break Y` / `verify Z` 형태 항목이 있으면 같은 Story Completion Criteria에 1:1 등장하는지 검증한다. 누락이 1건이면 NOTE, 2건 이상이면 FAIL.)

- [ ] 5. Story 타입 정확성 (Story Type Accuracy)
  Evidence: (verify each Story's Type matches the file-path decision table below.
  Use decidable rules (file path, type enum match) only — do not use subjective judgments such as "behavioral change" as evaluation criteria.
  Path triggers (e.g., `scripts/`) take precedence over extension triggers — a `.ts` file under `scripts/` is `infra`, not `refactor`/`tdd`.

| Type | Trigger (file path / extension) |
|------|---------------------------------|
| `tdd` | `.ts`/`.js`/`.py` source under test scope; Tasks include test authoring |
| `config` | `.md`/`.yml`/`.json`/`.toml` settings, prompts, rules, contracts |
| `infra` | `scripts/`, build/deploy tooling, executable Bash/Node CLI |
| `refactor` | `.ts`/`.js`/`.py` restructuring with existing test coverage |
| `prompt` | Eval Case가 명시적으로 존재할 때만 `prompt`. .md 파일 변경이라도 Eval Case가 없으면 `config`. |

  Story Type 값이 열거형 `tdd|config|infra|refactor|prompt` 외 (`docs`·`feat`·`chore` 등 Commit type 포함)이면 즉시 FAIL.
  Mismatch between stated type and table trigger → FAIL.

  For `prompt` type Stories — additional validation (spec §3.5):
  - Eval Case count < 2 → NOTE
  - Any Eval Case missing Input field → FAIL
  - `direct` Eval Case missing Expected field → FAIL
  - `rubric` Eval Case missing Criteria, Rubric, or Pass field → FAIL
  - `judge` Eval Case missing Expected, Judge Criteria, or Pass field → FAIL
  - Missing `Acceptance: N/M eval 통과` line → NOTE
  - N > M or N < 1 in Acceptance → FAIL)

- [ ] 6. Story 규모 적정성 (Story Size Appropriate)
  Evidence: (verify each Story fits within a single commit unit.
  Too large: Story spans multiple independent concerns that could be separate Stories → NOTE or FAIL.
  Too small: trivially simple steps bundled as a Story → NOTE.
  Size concerns that would make review or rollback impractical → FAIL.)

- [ ] 7. 구현 순서 타당성 (Implementation Order Valid)
  Evidence: (verify the stated story execution order respects all dependency relationships.
  Check: does any Story depend on an artifact produced by a later Story?
  Does the plan's dependency annotation match the actual order?
  Out-of-order dependency → FAIL.
  Implicit dependency not documented in the plan → NOTE.)

- [ ] 8. 범위 초과 없음 (No Scope Creep)
  Evidence: (verify no Story implements functionality beyond the spec's stated scope.
  Check: for each Story, confirm it maps to a spec requirement.
  Stories without a corresponding spec requirement → FAIL.
  Convenience additions or "while we're at it" work → FAIL.)
