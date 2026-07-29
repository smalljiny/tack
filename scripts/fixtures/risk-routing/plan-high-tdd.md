### [ ] Story 1: 세션 갱신 체인 구현

- **Type**: tdd
- **Risk Tier**: high (규칙 1 — affected paths가 보안 마커를 포함)
- **Goal**: 만료된 세션을 자동 갱신하는 체인을 구현한다.
- **Tasks**:
  - [ ] T1.1 — Add the refresh entry point
  - [ ] T1.2 — Wire the refresh chain into the request pipeline
- **Completion Criteria**:
  - [ ] 만료 세션 요청이 갱신 후 성공한다
- **Commit**: `feat(auth): add session refresh chain`
