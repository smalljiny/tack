---
version: 1
name: spec-review-pending-pr-dependency
description: Codex spec-review가 미병합 PR의 파일을 "없음"으로 판단해 NOT READY를 반복할 때의 해결 패턴
origin: learned
learned_at: 2026-04-25
---

## When to Activate

스펙이 현재 브랜치(develop)에 없는 파일에 의존할 때 — 예를 들어 다른 PR에서 추가될 스킬, 커맨드, 문서를 참조하는 스펙. Codex spec-review가 실제 파일시스템을 체크하므로 NOT READY가 반복 반환된다.

## Pattern

스펙 최상단에 **"구현 선행 조건"** 표를 추가해 현재 미충족 상태를 명시한다.
`/dev:plan`을 실행하기 전 해당 PR이 병합되어야 함을 선언한다.

```markdown
**구현 선행 조건 — 현재 미충족:**

| 파일 | 현재 상태 | 충족 방법 |
|------|----------|-----------|
| `.claude/skills/wf-deep-research/SKILL.md` | 미존재 | PR #15 (`feature/wf-deep-research`) `develop` 병합 |
| `.claude/skills/skill-registry/SKILL.md`   | 미존재 | 동상 |

`/dev:plan`을 실행하기 전에 PR #15가 병합되어야 한다.
```

설계 섹션(역할 정의 등)은 **병합 후 존재할 상태를 전제로** 작성하되,
호출 계약 주석에 `"PR #15 병합 후 구현 단계에서 검증"` 한 줄을 추가해 내부 일관성을 유지한다.

## Why It Works

Codex spec-review 스킬은 `ls` / `cat`으로 실제 파일을 확인한다.
파일이 없으면 구현 가능성 체크(Gate 7)에서 FAIL을 반환한다.
선행 조건 표가 있으면 리뷰어가 "설계는 병합 후 전제"임을 인식하고
파일 부재를 게이트 실패가 아닌 선행 조건 미충족으로 취급한다.
