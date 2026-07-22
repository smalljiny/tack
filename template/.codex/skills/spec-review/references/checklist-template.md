# Spec Review Checklist Template

Use all items. Final decision rules:
- All PASS → **READY**
- Any FAIL → **NOT READY**
- All PASS but some NOTE observations → **READY WITH NOTE**

---

- [ ] 1. 목표 명확성 (Clarity of Intent)
  Evidence: (verify Goals section is specific and verifiable — not vague aspirations.
  Each goal should answer "how will we know this is done?")

- [ ] 2. Non-goals 명시 (Non-goals Defined)
  Evidence: (verify Non-goals section explicitly states what this spec does NOT cover.
  Absence of Non-goals section → FAIL.
  Vague or empty Non-goals → FAIL.)

- [ ] 3. 아키텍처 충분성 (Architecture Sufficient for Planning)
  Evidence: (verify the spec contains a planning structure section with enough detail to decompose into tasks.
  Accepted forms: `## 3. 아키텍처` (code/feature topics) or `## 3. 역할 정의` or equivalent (workflow/policy/role topics).
  For code topics: must include overall structure, main components, and interfaces or data model where applicable.
  For non-code topics: must describe role boundaries, responsibility separation, or workflow structure in enough detail for planning.
  Missing any planning structure section → FAIL.
  Present but too vague to decompose into tasks → FAIL.)

- [ ] 4. 의사결정 근거 (Decision Rationale Documented)
  Evidence: (verify Design Decisions table exists and each row has a non-empty Rationale.
  Decisions without rationale → FAIL.
  Missing Design Decisions section entirely → FAIL.)

- [ ] 5. Open Questions 명시 (Open Questions Documented)
  Evidence: (verify Open Questions section exists.
  Unresolved decisions that affect implementation scope must be listed here, not assumed away.
  Missing section or section present but clearly incomplete given spec content → FAIL.)

- [ ] 6. 내부 일관성 (Internal Consistency)
  Evidence: (verify no contradictions between sections.
  Check: Goals vs Architecture, Goals vs Non-goals, Architecture vs Design Decisions.
  Any direct contradiction → FAIL.)

- [ ] 7. 구현 가능성 (Implementation Readiness)
  Evidence: (verify spec is concrete enough for implementation to begin.
  Must not rely on undefined external systems, unknown APIs, or decisions deferred without tracking.
  Blockers not listed in Open Questions → FAIL.)

- [ ] 8. 범위 적정성 (Scope Appropriate)
  Evidence: (verify spec is neither too large nor too small.
  Too large: covers multiple independent deployable units that should be separate specs → NOTE or FAIL.
  Too small: trivially simple, does not warrant a spec → NOTE.
  Scope concerns that would block planning → FAIL.)
