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
  Documented sequential dependencies with clear rationale → acceptable.

  `scaffold` carve-out — `scaffold` Story는 독립 실행·커밋 가능 기준은 충족하되, 독립 배포 가능 기준은
  동일 PR 내 후속 구현 Story와 묶인 PR 단위에서 평가한다. `scaffold` Story가 단독으로 배포 가능하지
  않다는 이유로 FAIL 처리하지 않는다.)

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
| `scaffold` | `Risk Tier == high`인 `tdd`/`refactor` Story의 분해 산물 — 시그니처·타입/인터페이스·호출·이벤트 체인 배선·throwing stub. Completion Criteria는 언어별 정적 검사 + entry 모듈 import 스모크. |

  Story Type 값이 열거형 `tdd|config|infra|refactor|prompt|scaffold` 외 (`docs`·`feat`·`chore` 등 Commit type 포함)이면 즉시 FAIL.
  Mismatch between stated type and table trigger → FAIL.

  `scaffold` carve-out — 선행 `scaffold` Story를 가진 `high` tier `tdd`·`refactor` Story는 골격 의례 충족으로 간주한다. 자기 자신의 scaffold Story가 없다는 이유로 FAIL 처리하지 않는다.
  또한 `Type: scaffold`로 선언된 Story는 위 표의 관계형 트리거(분해 산물)로 판정하며, 확장자 트리거(`tdd`/`refactor` 행)와의 mismatch만으로 FAIL 처리하지 않는다.

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
